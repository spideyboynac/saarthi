import time
import logging
import traceback
from typing import Optional, Any, Dict, List
from contextlib import contextmanager

logger = logging.getLogger("pipeline.diagnosis")

class StageLogResult:
    def __init__(self, stage_num: int, stage_name: str):
        self.stage_num = stage_num
        self.stage_name = stage_name
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.duration_ms: float = 0.0
        self.status: str = "PENDING"
        self.error_type: Optional[str] = None
        self.error_message: Optional[str] = None
        self.traceback_str: Optional[str] = None
        self.details: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "stage_num": self.stage_num,
            "stage_name": self.stage_name,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "details": self.details,
        }
        if self.status == "FAILURE":
            res["error_type"] = self.error_type
            res["error_message"] = self.error_message
            res["traceback"] = self.traceback_str
        return res

    def print_summary(self):
        status_symbol = "✓" if self.status == "SUCCESS" else ("⚠ SKIPPED/PASS" if self.status == "PASS_THROUGH" else "❌ FAILED")
        print(f"  Stage {self.stage_num:2d}: [{self.stage_name}] → {status_symbol} ({self.duration_ms:.2f} ms)")
        if self.details:
            for k, v in self.details.items():
                print(f"            {k}: {v}")
        if self.status == "FAILURE":
            print(f"            ERROR [{self.error_type}]: {self.error_message}")
            if self.traceback_str:
                print("            FULL TRACEBACK:")
                for line in self.traceback_str.strip().split("\n"):
                    print(f"              {line}")


class PipelineTracker:
    def __init__(self, call_id: str = "test-call"):
        self.call_id = call_id
        self.stage_logs: List[StageLogResult] = []

    @contextmanager
    def track_stage(self, stage_num: int, stage_name: str):
        log = StageLogResult(stage_num, stage_name)
        log.start_time = time.perf_counter()
        try:
            yield log
            if log.status == "PENDING":
                log.status = "SUCCESS"
        except Exception as e:
            log.status = "FAILURE"
            log.error_type = type(e).__name__
            log.error_message = str(e)
            log.traceback_str = traceback.format_exc()
            # Log full exception traceback
            logger.error(f"[Stage {stage_num:2d} - {stage_name}] FAILED: {e}\n{log.traceback_str}")
            # We don't re-raise so pipeline diagnosis can complete or capture downstream effect
        finally:
            log.end_time = time.perf_counter()
            log.duration_ms = (log.end_time - log.start_time) * 1000.0
            self.stage_logs.append(log)

    def print_pipeline_report(self, title: str = "Pipeline Execution Report"):
        print("\n" + "=" * 80)
        print(f" {title} | Call ID: {self.call_id}")
        print("=" * 80)
        total_time = sum(l.duration_ms for l in self.stage_logs)
        for log in self.stage_logs:
            log.print_summary()
        print("-" * 80)
        print(f" Total Pipeline Execution Time: {total_time:.2f} ms")
        print("=" * 80 + "\n")
