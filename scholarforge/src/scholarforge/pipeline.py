"""Main Pipeline Orchestrator."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import ScholarForgeConfig
from .gap_analysis.analyzer import analyze_gaps
from .gap_analysis.missing_md import generate_missing_md, parse_missing_md
from .gap_analysis.models import GapReport, HumanInput
from .literature import extract_knowledge_cards, search_all
from .literature.models import KnowledgeCard, PaperResult
from .llm.provider import LLMProvider
from .review.peer_review import review_paper
from .utils.logger import get_logger, setup_logging
from .verification import verify_all_citations
from .verification.models import Citation, VerificationReport
from .writing import compile_paper, generate_outline, write_section
from .writing.anti_slop import SlopDetector, rewrite_flagged
from .writing.models import PaperDraft, PaperOutline
from .repo_reader import RepoContext

logger = get_logger(__name__)


class PipelineState:
    """Pipeline state tracking."""
    
    def __init__(
        self,
        run_id: str,
        current_stage: int = 0,
        stage_statuses: Optional[dict] = None,
        topic: str = "",
        passed_gates: Optional[list] = None
    ):
        self.run_id = run_id
        self.current_stage = current_stage
        self.stage_statuses = stage_statuses or {}
        self.topic = topic
        self.created_at = datetime.now().isoformat()
        self.passed_gates: list[str] = passed_gates or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "current_stage": self.current_stage,
            "stage_statuses": self.stage_statuses,
            "topic": self.topic,
            "created_at": self.created_at,
            "passed_gates": self.passed_gates
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        state = cls(
            run_id=data["run_id"],
            current_stage=data.get("current_stage", 0),
            stage_statuses=data.get("stage_statuses", {}),
            topic=data.get("topic", ""),
            passed_gates=data.get("passed_gates", [])
        )
        state.created_at = data.get("created_at", datetime.now().isoformat())
        return state


class Pipeline:
    """Main pipeline orchestrator."""
    
    STAGE_NAMES = {
        1: "topic_decomposition",
        2: "literature_search",
        3: "knowledge_extraction",
        4: "citation_verification",
        5: "gap_analysis",
        6: "paper_writing",
        7: "anti_slop_check",
        8: "peer_review",
        9: "latex_compilation"
    }
    
    def __init__(self, config: ScholarForgeConfig):
        """Initialize pipeline.
        
        Args:
            config: Complete configuration
        """
        self.config = config
        self.llm = LLMProvider(config.llm)
        self.state: Optional[PipelineState] = None
        self.output_dir: Path = Path(config.project.output_dir)
        
        # Setup logging
        setup_logging(
            level=config.logging.level,
            log_file=config.logging.file,
            console=True
        )
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self, topic: str, repo_context: Optional[RepoContext] = None) -> dict[str, Any]:
        """Run the full pipeline.
        
        Args:
            topic: Research topic
            
        Returns:
            Pipeline results
        """
        self.state = PipelineState(
            run_id=f"sf-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            topic=topic
        )
        
        logger.info(f"Starting pipeline for topic: {topic}")
        logger.info(f"Run ID: {self.state.run_id}")
        
        if repo_context:
            logger.info(f"Repository context provided: {repo_context.readme_path or 'no README'}, {len(repo_context.code_files)} code files")
        
        results = {}
        
        try:
            # Stage 1: Topic Decomposition
            results["research_plan"] = self._stage1_topic_decomposition(topic, repo_context)
            
            # Stage 2: Literature Search
            results["papers"] = self._stage2_literature_search(topic)
            
            # Stage 3: Knowledge Extraction
            results["knowledge_cards"] = self._stage3_knowledge_extraction(topic, results["papers"])
            
            # Stage 4: Citation Verification
            results["verification"] = self._stage4_citation_verification(results["papers"])
            
            # Check gate: literature_review
            if self._check_gate("literature_review"):
                logger.info("Pausing at literature_review gate")
                self._save_state()
                return {"status": "paused", "gate": "literature_review", "run_id": self.state.run_id}
            
            # Stage 5: Gap Analysis
            results["gap_report"] = self._stage5_gap_analysis(topic, results["knowledge_cards"])
            
            # Generate READMEMISSING.md
            missing_md = generate_missing_md(
                results["gap_report"],
                topic,
                self.state.run_id,
                len(results["papers"])
            )
            missing_path = self.output_dir / "stage-5" / "READMEMISSING.md"
            missing_path.parent.mkdir(parents=True, exist_ok=True)
            missing_path.write_text(missing_md)
            logger.info(f"Generated READMEMISSING.md: {missing_path}")
            
            # Check gate: gap_analysis
            if self._check_gate("gap_analysis"):
                logger.info("Pausing at gap_analysis gate")
                self._save_state()
                return {
                    "status": "paused",
                    "gate": "gap_analysis",
                    "run_id": self.state.run_id,
                    "missing_md_path": str(missing_path)
                }
            
            # Continue with remaining stages
            return self._continue_pipeline(results, repo_context)
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self._save_state()
            raise
    
    def _continue_pipeline(self, results: dict, repo_context: Optional[RepoContext] = None) -> dict[str, Any]:
        """Continue pipeline after human input."""
        
        # Load human input
        missing_path = self.output_dir / "stage-5" / "READMEMISSING.md"
        if missing_path.exists():
            human_input = parse_missing_md(str(missing_path))
            if isinstance(human_input, Exception):
                human_input = HumanInput()
        else:
            human_input = HumanInput()
        
        # Stage 6: Paper Writing (skip if already done)
        if not (self.output_dir / "stage-6" / "result.json").exists():
            knowledge_cards = results.get("knowledge_cards") or results.get("knowledge_extraction")
            results["draft"] = self._stage6_paper_writing(
                self.state.topic,
                human_input,
                knowledge_cards,
                results.get("verification") or results.get("citation_verification"),
                repo_context
            )
        else:
            results["draft"] = results.get("paper_writing") or results.get("draft")

        # Stage 7: Anti-Slop Check (skip if already done)
        if not (self.output_dir / "stage-7" / "result.json").exists():
            results["slop_report"] = self._stage7_anti_slop_check(results["draft"])

        # Stage 8: Peer Review (skip if already done)
        if not (self.output_dir / "stage-8" / "result.json").exists():
            results["reviews"] = self._stage8_peer_review(results["draft"])

        # Check gate: final_review
        if self._check_gate("final_review"):
            logger.info("Pausing at final_review gate")
            self._save_state()
            return {
                "status": "paused",
                "gate": "final_review",
                "run_id": self.state.run_id
            }

        # Stage 9: LaTeX Compilation
        results["latex"] = self._stage9_latex_compilation(
            results["draft"],
            results.get("verification") or results.get("citation_verification")
        )
        
        self.state.current_stage = 9
        self._save_state()
        
        logger.info("Pipeline complete!")
        return {
            "status": "complete",
            "run_id": self.state.run_id,
            "output_dir": str(self.output_dir),
            "results": results
        }
    
    def resume(self, run_id: str, repo_context: Optional[RepoContext] = None) -> dict[str, Any]:
        """Resume a paused pipeline.
        
        Args:
            run_id: Pipeline run ID
            repo_context: Optional repository context (if not provided, will try to load from state)
            
        Returns:
            Pipeline results
        """
        state_path = self.output_dir / "pipeline_state.json"
        
        if not state_path.exists():
            raise ValueError(f"No pipeline state found for run_id: {run_id}")
        
        with open(state_path) as f:
            self.state = PipelineState.from_dict(json.load(f))
        
        if self.state.run_id != run_id:
            raise ValueError(f"Run ID mismatch: {self.state.run_id} != {run_id}")
        
        logger.info(f"Resuming pipeline: {run_id} from stage {self.state.current_stage}")

        # Load previous results
        results = self._load_stage_results()

        # If paused at literature_review gate (stage 4 done, stage 5 not yet run),
        # run stage 5 and handle the gap_analysis gate before continuing
        stage5_path = self.output_dir / "stage-5" / "result.json"
        if not stage5_path.exists():
            knowledge_cards = results.get("knowledge_cards") or results.get("knowledge_extraction")
            results["gap_report"] = self._stage5_gap_analysis(self.state.topic, knowledge_cards)

            missing_md = generate_missing_md(
                results["gap_report"],
                self.state.topic,
                self.state.run_id,
                len(results.get("papers", results.get("literature_search", [])))
            )
            missing_path = self.output_dir / "stage-5" / "READMEMISSING.md"
            missing_path.parent.mkdir(parents=True, exist_ok=True)
            missing_path.write_text(missing_md)
            logger.info(f"Generated READMEMISSING.md: {missing_path}")

            if self._check_gate("gap_analysis"):
                logger.info("Pausing at gap_analysis gate")
                self._save_state()
                return {
                    "status": "paused",
                    "gate": "gap_analysis",
                    "run_id": self.state.run_id,
                    "missing_md_path": str(missing_path)
                }

        return self._continue_pipeline(results, repo_context)
    
    def _stage1_topic_decomposition(self, topic: str, repo_context: Optional[RepoContext] = None) -> dict:
        """Stage 1: Decompose topic into research questions."""
        logger.info("Stage 1: Topic Decomposition")
        
        # Build context from README and code if provided
        context_str = ""
        if repo_context:
            if repo_context.readme_content:
                context_str += f"\n\nREADME Content:\n{repo_context.readme_content[:3000]}"
            if repo_context.code_files:
                context_str += f"\n\nCode Repository Files: {len(repo_context.code_files)} files"
                # Include a summary of key files
                key_files = repo_context.code_files[:5]
                for f in key_files:
                    context_str += f"\n- {f['path']} ({f['lines']} lines)"
        
        system = """You are a research planning assistant. Given a research topic and optional repository context, decompose it into research questions and search queries.

If repository context (README and code files) is provided, use it to:
1. Understand what the project does
2. Identify the key technical contributions
3. Formulate research questions that align with the implementation
4. Generate search queries that find related work

Respond ONLY in valid JSON:
{
  "research_question": "...",
  "sub_questions": ["..."],
  "search_queries": ["..."],
  "keywords": ["..."]
}"""
        
        user_prompt = f"Research topic: {topic}"
        if context_str:
            user_prompt += f"\n\nRepository Context:{context_str}"
        
        result = self.llm.complete_json(system, user_prompt)
        
        self._save_stage_result(1, result)
        return result
    
    def _stage2_literature_search(self, topic: str) -> list[PaperResult]:
        """Stage 2: Search for relevant literature."""
        logger.info("Stage 2: Literature Search")
        
        papers = search_all(topic, self.config.literature, self.llm)
        
        papers_data = [p.to_dict() for p in papers]
        self._save_stage_result(2, {"papers": papers_data, "count": len(papers)})
        
        return papers
    
    def _stage3_knowledge_extraction(self, topic: str, papers: list[PaperResult]) -> list[KnowledgeCard]:
        """Stage 3: Extract knowledge from papers."""
        logger.info("Stage 3: Knowledge Extraction")
        
        cards = extract_knowledge_cards(topic, papers, self.llm)
        
        cards_data = [c.to_dict() for c in cards]
        self._save_stage_result(3, {"cards": cards_data, "count": len(cards)})
        
        return cards
    
    def _stage4_citation_verification(self, papers: list[PaperResult]) -> VerificationReport:
        """Stage 4: Verify all citations."""
        logger.info("Stage 4: Citation Verification")
        
        # Convert papers to citations
        citations = [
            Citation(
                key=f"paper_{i}",
                title=p.title,
                authors=p.authors,
                arxiv_id=p.arxiv_id,
                doi=p.doi,
                year=p.year,
                venue=p.venue
            )
            for i, p in enumerate(papers)
        ]
        
        s2_api_key = self.config.literature.get_s2_api_key()
        stage_dir = self.output_dir / "stage-4"
        
        report = verify_all_citations(
            citations,
            self.config.verification,
            s2_api_key,
            str(stage_dir)
        )
        
        self._save_stage_result(4, report.to_dict())
        
        return report
    
    def _stage5_gap_analysis(self, topic: str, cards: list[KnowledgeCard]) -> GapReport:
        """Stage 5: Analyze gaps in knowledge."""
        logger.info("Stage 5: Gap Analysis")
        
        # Summarize knowledge cards
        knowledge_summary = "\n\n".join([
            f"Paper: {c.paper.title}\n"
            f"Findings: {', '.join(c.key_findings[:3])}\n"
            f"Method: {c.methodology[:200]}..."
            for c in cards[:10]
        ])
        
        report = analyze_gaps(topic, len(cards), knowledge_summary, self.llm)
        
        self._save_stage_result(5, report.to_dict())
        
        return report
    
    def _stage6_paper_writing(
        self,
        topic: str,
        human_input: HumanInput,
        cards: list[KnowledgeCard],
        verification: VerificationReport,
        repo_context: Optional[RepoContext] = None
    ) -> PaperDraft:
        """Stage 6: Write the paper."""
        logger.info("Stage 6: Paper Writing")
        
        # Build citation list from verified papers
        verified_citations = [
            {
                "key": f"paper_{i}",
                "title": v.citation.title,
                "authors": v.citation.authors,
                "arxiv_id": v.citation.arxiv_id,
                "doi": v.citation.doi,
                "year": v.citation.year,
                "venue": v.citation.venue
            }
            for i, v in enumerate(verification.details)
            if v.final_verified
        ]
        
        # Summarize knowledge
        knowledge_summary = "\n\n".join([
            f"Paper: {c.paper.title}\nFindings: {', '.join(c.key_findings[:3])}"
            for c in cards[:10]
        ])
        
        # Add repo context to knowledge summary if available
        if repo_context:
            knowledge_summary += "\n\n=== REPOSITORY CONTEXT ===\n"
            if repo_context.readme_content:
                knowledge_summary += f"\nREADME:\n{repo_context.readme_content[:2000]}"
            if repo_context.code_files:
                knowledge_summary += f"\n\nKey Implementation Files:\n"
                for f in repo_context.code_files[:3]:
                    knowledge_summary += f"\n{f['path']}:\n{f['content'][:1000]}\n"
        
        # Generate outline
        outline = generate_outline(
            topic,
            human_input.to_dict(),
            verified_citations,
            knowledge_summary,
            self.config.paper,
            self.llm
        )
        
        # Write each section
        sections = {}
        for section in outline.sections:
            content = write_section(
                outline.title,
                section,
                verified_citations,
                sections,
                human_input.to_dict(),
                self.config.paper.conference,
                self.llm
            )
            sections[section.title] = content
        
        draft = PaperDraft(
            title=outline.title,
            abstract=outline.abstract,
            sections=sections,
            outline=outline,
            citations=[c["key"] for c in verified_citations]
        )
        
        # Save draft
        draft_path = self.output_dir / "stage-6" / "paper_draft.md"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(draft.get_full_text())
        
        self._save_stage_result(6, draft.to_dict())
        
        return draft
    
    def _stage7_anti_slop_check(self, draft: PaperDraft) -> dict:
        """Stage 7: Check for AI-writing patterns."""
        logger.info("Stage 7: Anti-Slop Check")
        
        detector = SlopDetector()
        full_text = draft.get_full_text()
        
        report = detector.scan(full_text)
        
        # Rewrite if needed
        if report.slop_score > 0.3 and not self.config.human_in_the_loop.auto_approve:
            logger.info(f"Slop score {report.slop_score:.2f}, rewriting flagged sections...")
            
            for section_name, content in draft.sections.items():
                section_flags = [
                    f for f in report.high_severity + report.medium_severity
                    if section_name.lower() in f.context.lower()
                ]
                
                if section_flags:
                    rewritten = rewrite_flagged(content, section_flags, self.llm)
                    draft.sections[section_name] = rewritten
        
        self._save_stage_result(7, report.to_dict())
        
        return report.to_dict()
    
    def _stage8_peer_review(self, draft: PaperDraft) -> dict:
        """Stage 8: Multi-agent peer review."""
        logger.info("Stage 8: Peer Review")
        
        reviews = review_paper(draft.get_full_text(), draft.outline, self.llm)
        
        # Save reviews
        reviews_path = self.output_dir / "stage-8" / "reviews.json"
        reviews_path.parent.mkdir(parents=True, exist_ok=True)
        reviews_path.write_text(json.dumps(reviews, indent=2))
        
        self._save_stage_result(8, reviews)
        
        return reviews
    
    def _stage9_latex_compilation(self, draft: PaperDraft, verification: VerificationReport) -> dict:
        """Stage 9: Compile to LaTeX."""
        logger.info("Stage 9: LaTeX Compilation")
        
        # Build citations
        verified_citations = [
            {
                "key": f"paper_{i}",
                "title": v.citation.title,
                "authors": v.citation.authors,
                "arxiv_id": v.citation.arxiv_id,
                "doi": v.citation.doi,
                "year": v.citation.year,
                "venue": v.citation.venue
            }
            for i, v in enumerate(verification.details)
            if v.final_verified
        ]
        
        output = compile_paper(
            draft,
            verified_citations,
            self.config.paper.conference,
            str(self.output_dir / "stage-9")
        )
        
        result = {
            "tex_path": output.tex_path,
            "bib_path": output.bib_path,
            "pdf_path": output.pdf_path,
            "figures_dir": output.figures_dir
        }
        
        self._save_stage_result(9, result)
        
        return result
    
    def _check_gate(self, gate_name: str) -> bool:
        """Check if we should pause at this gate.

        Returns:
            True if should pause, False if should continue
        """
        if self.config.human_in_the_loop.auto_approve:
            return False

        if gate_name in self.state.passed_gates:
            return False

        if gate_name in self.config.human_in_the_loop.gate_stages:
            # Mark gate as passed so next resume skips it
            self.state.passed_gates.append(gate_name)
            return True

        return False
    
    def _save_state(self) -> None:
        """Save pipeline state to disk."""
        state_path = self.output_dir / "pipeline_state.json"
        with open(state_path, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)
        logger.debug(f"Saved pipeline state: {state_path}")
    
    def _save_stage_result(self, stage: int, result: dict) -> None:
        """Save stage result to disk."""
        stage_dir = self.output_dir / f"stage-{stage}"
        stage_dir.mkdir(parents=True, exist_ok=True)
        
        result_path = stage_dir / "result.json"
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        self.state.current_stage = stage
        self.state.stage_statuses[self.STAGE_NAMES.get(stage, f"stage_{stage}")] = "complete"
        self._save_state()
        
        logger.info(f"Stage {stage} complete: {self.STAGE_NAMES.get(stage, 'unknown')}")
    
    def _load_stage_results(self) -> dict:
        """Load all stage results from disk."""
        results = {}

        for i in range(1, 10):
            result_path = self.output_dir / f"stage-{i}" / "result.json"
            if result_path.exists():
                with open(result_path) as f:
                    data = json.load(f)

                # Deserialize typed objects so downstream stages work correctly
                if i == 2:  # literature_search: list of PaperResult dicts
                    if isinstance(data, list):
                        data = [PaperResult.from_dict(p) if isinstance(p, dict) else p for p in data]
                elif i == 3:  # knowledge_extraction: {"cards": [...], "count": N}
                    if isinstance(data, dict) and "cards" in data:
                        data = [KnowledgeCard.from_dict(c) if isinstance(c, dict) else c for c in data["cards"]]
                elif i == 4:  # citation_verification: VerificationReport
                    if isinstance(data, dict):
                        data = VerificationReport.from_dict(data)
                elif i == 6:  # paper_writing: PaperDraft
                    if isinstance(data, dict):
                        data = PaperDraft.from_dict(data)

                results[self.STAGE_NAMES.get(i, f"stage_{i}")] = data

        # Provide aliases so both old and new key names work
        if "knowledge_extraction" in results:
            results["knowledge_cards"] = results["knowledge_extraction"]
        if "citation_verification" in results:
            results["verification"] = results["citation_verification"]

        return results
