# Design Document: Camera Visual Context Analyzer

## 1. Updated Project Context

The original system classified live camera frames as HIGH, MEDIUM, or LOW quality using an LLM, and auto-alerted on LOW. This approach had a fundamental limitation: the LLM acted as an autonomous decision-maker, but LLM outputs are not reliably calibrated — a self-reported "HIGH confidence" classification cannot be fully trusted.

The updated system shifts the LLM's role from **classifier** to **explainer**. An external trigger (e.g., an OpenCV-based discrepancy detector) determines that something is worth investigating. The LLM then adds visual context — describing what it observes and suggesting possible causes — so that a human can make the final suppression or escalation decision.

This design:
- Uses the LLM for what it does well: natural language reasoning over images
- Removes the LLM from autonomous decision-making
- Creates a human-in-the-loop workflow where alerts are enriched, not generated, by the LLM
- Produces auditable reasoning for every flagged camera

---

## 2. High Level Design

```
External trigger (e.g. OpenCV discrepancy detector)
    |
    v
DiscrepancyExplainer
    - Accepts: benchmark image + live frame
    - Invokes: LLM (AWS Bedrock Claude via LangChain)
    - Returns: VisualContext (summary, possible_causes, comparison_notes)
    |
    v
Alert (SQS)
    - Payload: camera_id + timestamp + VisualContext
    |
    v
Human reviewer
    - Reads: explanation + image pair
    - Decides: suppress / escalate
```

The `DiscrepancyExplainer` is a standalone, callable component. It has no knowledge of OpenCV, thresholds, or alert routing. It accepts two images and returns a structured explanation. The caller is responsible for triggering it and handling the result.

---

## 3. Workflow

1. An external component detects a potential discrepancy for a given camera and calls `DiscrepancyExplainer.explain(benchmark_image, live_frame, camera_id)`.
2. The explainer builds a multimodal prompt containing both images and asks the LLM to describe what differs and why it might matter.
3. The LLM returns a structured `VisualContext` object.
4. The caller sends an alert to SQS with the camera ID, timestamp, and full `VisualContext`.
5. A human reviewer receives the alert, views the image pair alongside the explanation, and decides whether to act.

---

## 4. Implementation Plan

### 4.1 Mock OpenCV Module

The OpenCV discrepancy detector is out of scope for this implementation. Instead, a mock module exposes the expected interface so the rest of the pipeline can be built and tested independently.

**Interface:**

```python
# discrepancy_detector.py

class DiscrepancyDetector:
    def detect(self, benchmark_image: ImageObject, live_frame: ImageObject, camera_id: str) -> bool:
        """
        Returns True if a discrepancy is detected and the explainer should be called.
        Mock implementation always returns True for non-None inputs.
        """
        return benchmark_image is not None and live_frame is not None
```

This interface is the only contract the rest of the system depends on. A real OpenCV implementation can replace this module without changing any other code.

---

### 4.2 LLM Visual Context

The `DiscrepancyExplainer` is the core new component. It accepts two images and returns a structured explanation from the LLM.

**Interface:**

```python
# discrepancy_explainer.py

class DiscrepancyExplainer:
    def __init__(self, logger: logging.Logger, llm: LLM):
        ...

    async def explain(
        self,
        benchmark_image: ImageObject,
        live_frame: ImageObject,
        camera_id: str
    ) -> VisualContext:
        """
        Compares live_frame against benchmark_image using the LLM vision model.
        Returns a structured visual explanation.
        """
        ...
```

**LLM prompt design:**

The system prompt instructs the LLM to act as an observer, not a judge:

```
You are analyzing a surveillance camera feed. You will be given two images:
1) A benchmark image representing the expected normal view for this camera.
2) A live frame captured recently from the same camera.

Describe what you observe in the live frame compared to the benchmark.
Do not classify quality as good or bad. Focus on:
- What visually differs between the two images
- Where in the frame the difference appears
- What might have caused it (physical, environmental, or technical)
```

The human message contains both images with text labels, identical in structure to the existing `analyze_single_image` prompt.

---

### 4.3 Data Contracts

**Input:**

```python
# Existing type — no changes needed
@dataclass
class ImageObject:
    filename: str
    base64: str
    media_type: str
```

**Output:**

```python
from pydantic import BaseModel

class VisualContext(BaseModel):
    summary: str            # One-sentence description of the key difference
    possible_causes: list[str]   # e.g. ["lens obstruction", "environmental fog"]
    comparison_notes: str   # Detailed observation comparing live frame to benchmark
```

---

### 4.4 Alert Payload

The SQS message sent to human reviewers:

```json
{
  "camera_id": "cam-001",
  "timestamp": "2026-03-09T14:23:01Z",
  "visual_context": {
    "summary": "Upper-left quadrant appears physically blocked",
    "possible_causes": ["lens obstruction", "camera vandalism"],
    "comparison_notes": "Benchmark shows a clear wide-angle street view with uniform lighting. The live frame has a uniform dark region covering approximately 30% of the upper-left area that is absent in the benchmark. The boundary of the dark region is sharp, suggesting a physical object rather than a lighting or environmental cause."
  }
}
```

No quality enum, no confidence score. The human reads the `visual_context` and decides.

---

## 5. Automated Testing with Promptfoo

Promptfoo is used to evaluate the `DiscrepancyExplainer`'s LLM prompt in isolation — verifying that the model produces useful, specific, and accurate explanations for known image pairs.

### 5.1 Test Cases

Each test case is a benchmark + live frame pair with a known discrepancy. The reference answers describe what a correct explanation should contain.

| Test case | Discrepancy | Key assertions |
|---|---|---|
| Clear camera | No discrepancy (control case) | Explanation notes images are similar; no obstruction language |
| Lens obstruction | Physical object blocking partial view | Mentions blocked/covered region; suggests physical cause |
| Blurry live frame | Live frame significantly blurrier than benchmark | Mentions blur or loss of detail; contrasts with sharp benchmark |
| Lighting change | Live frame much darker or overexposed | Mentions brightness/lighting difference; suggests environmental cause |
| Camera drift | Camera angle shifted from benchmark | Mentions shift in perspective or composition change |

---

### 5.2 Assertion Strategy

Each test uses a combination of assertion types suited to the nature of the check:

**`factuality`** — verifies the explanation captured the correct core observation:
```yaml
- type: factuality
  value: "The live frame shows a region of the image that is blocked or obscured compared to the benchmark"
```

**`llm-rubric`** — verifies explanation specificity and structure:
```yaml
- type: llm-rubric
  value: "Response identifies a specific region of the frame affected (e.g., upper-left, center, bottom)"

- type: llm-rubric
  value: "Response suggests at least one possible cause for the observed difference"

- type: llm-rubric
  value: "Response does not use quality labels like HIGH, MEDIUM, or LOW"
```

**`contains`** — verifies key terms appear for high-signal cases:
```yaml
- type: contains
  value: "obstruct"   # for obstruction test case
```

The control case (no discrepancy) uses a negative rubric:
```yaml
- type: llm-rubric
  value: "Response does not describe any obstruction, blur, or significant difference between the two images"
```

---

### 5.3 Promptfoo Configuration

**`prompt.json`** — two-image multimodal prompt:

```json
[
  {
    "role": "system",
    "content": "You are analyzing a surveillance camera feed. You will be given two images: 1) A benchmark image representing the expected normal view. 2) A live frame captured recently. Describe what you observe in the live frame compared to the benchmark. Do not classify quality as good or bad. Focus on what visually differs, where in the frame, and what might have caused it."
  },
  {
    "role": "user",
    "content": [
      {"type": "text", "text": "Benchmark image:"},
      {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "{{benchmark}}"}},
      {"type": "text", "text": "Live frame:"},
      {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "{{live_frame}}"}}
    ]
  }
]
```

**`promptfooconfig.yaml`**:

```yaml
prompts:
  - file://prompt.json

providers:
  - id: bedrock:anthropic.claude-3-5-sonnet-20241022-v2:0
    config:
      region: us-east-1

tests:
  - description: "Control — no discrepancy"
    vars:
      benchmark: "file://test_images/clear_benchmark.jpg"
      live_frame: "file://test_images/clear_live.jpg"
    assert:
      - type: llm-rubric
        value: "Response does not describe any obstruction, blur, or significant difference between the two images"

  - description: "Lens obstruction"
    vars:
      benchmark: "file://test_images/clear_benchmark.jpg"
      live_frame: "file://test_images/obstructed_live.jpg"
    assert:
      - type: factuality
        value: "The live frame shows a region of the image that is blocked or obscured compared to the benchmark"
      - type: llm-rubric
        value: "Response identifies a specific region of the frame affected"
      - type: llm-rubric
        value: "Response suggests at least one possible physical cause"
      - type: contains
        value: "obstruct"

  - description: "Blurry live frame"
    vars:
      benchmark: "file://test_images/clear_benchmark.jpg"
      live_frame: "file://test_images/blurry_live.jpg"
    assert:
      - type: factuality
        value: "The live frame is blurry or lacks the sharpness visible in the benchmark"
      - type: llm-rubric
        value: "Response contrasts the sharpness or detail level between the two images"

  - description: "Lighting change"
    vars:
      benchmark: "file://test_images/clear_benchmark.jpg"
      live_frame: "file://test_images/dark_live.jpg"
    assert:
      - type: factuality
        value: "The live frame is significantly darker than the benchmark"
      - type: llm-rubric
        value: "Response mentions lighting, brightness, or exposure as a factor"
      - type: llm-rubric
        value: "Response suggests an environmental or technical cause"

  - description: "Camera drift"
    vars:
      benchmark: "file://test_images/clear_benchmark.jpg"
      live_frame: "file://test_images/drifted_live.jpg"
    assert:
      - type: factuality
        value: "The camera angle or framing in the live frame differs from the benchmark"
      - type: llm-rubric
        value: "Response notes a shift in perspective, composition, or viewing angle"
```

---

### 5.4 Running the Evaluation

```bash
# Install promptfoo
npm install -g promptfoo

# Set AWS credentials
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1

# Run evaluation
npx promptfoo eval

# View results in browser
npx promptfoo view
```

To compare explanation quality across model versions or providers, add additional entries to `providers` in the config. Promptfoo will run every test against every provider and display a side-by-side comparison table.
