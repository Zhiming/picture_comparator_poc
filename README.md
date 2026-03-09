# Camera Visual Context Analyzer

Automated surveillance camera monitoring system that uses AWS Bedrock Claude (multimodal vision) to explain visual discrepancies between live frames and benchmark images, enabling human-in-the-loop incident review.

## Overview

An external discrepancy detector (e.g. OpenCV-based) determines that a camera frame differs from its benchmark. This system then invokes an LLM to describe what changed and why it might matter — producing structured visual context for a human reviewer to act on.

The LLM acts as an **explainer**, not a classifier. It does not make autonomous quality decisions. A human reads the explanation and decides whether to suppress or escalate.

## Data Flow

```
DynamoDB (camera_registry)
    -> camera IDs for a given data center
    -> benchmark image S3 URL per camera

Kinesis Video Streams
    -> live frame (base64 JPEG) per camera

S3
    -> benchmark image (base64) per camera

External trigger (discrepancy detector)
    -> calls DiscrepancyExplainer with benchmark + live frame

LLM (AWS Bedrock Claude via LangChain)
    -> VisualContext (summary, possible_causes, comparison_notes)

SQS
    -> alert payload: camera_id + timestamp + VisualContext

Human reviewer
    -> reads explanation + image pair, decides to suppress or escalate
```

## Requirements

- Python 3.12+
- AWS account with Bedrock, DynamoDB, Kinesis Video Streams, S3, and SQS access
- AWS credentials with appropriate permissions

## Setup

```bash
# Install dependencies (uv manages the virtualenv automatically)
uv sync

# Create .env file
cp .env.example .env
```

Required `.env` variables:

```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
PROVIDER=anthropic
```

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `discrepancy_explainer.py` | Core component. Accepts benchmark image + live frame, builds a multimodal LangChain prompt, and returns a structured `VisualContext` explanation. |
| `discrepancy_detector.py` | Mock OpenCV discrepancy detector. Returns `True` if both images are non-None. Real OpenCV implementation replaces this without changing any other code. |
| `image_loader.py` | `ImageObject` dataclass (filename, base64, media_type); image loading and validation. |

## Alert Payload

SQS messages sent to human reviewers contain structured visual context — no quality enum, no confidence score:

```json
{
  "camera_id": "cam-001",
  "timestamp": "2026-03-09T14:23:01Z",
  "visual_context": {
    "summary": "Upper-left quadrant appears physically blocked",
    "possible_causes": ["lens obstruction", "camera vandalism"],
    "comparison_notes": "Benchmark shows a clear wide-angle street view. The live frame has a uniform dark region covering approximately 30% of the upper-left area, absent in the benchmark. The sharp boundary suggests a physical object rather than a lighting or environmental cause."
  }
}
```

## LangChain Prompt Structure

The multimodal prompt uses LangChain LCEL (`prompt | llm | parser`):

1. `SystemMessage` — instructs the LLM to describe differences without quality labeling
2. `SystemMessage` — `JsonOutputParser` format instructions for `VisualContext`
3. `HumanMessage` — benchmark image + live frame as `data:<media_type>;base64,<data>` URLs

## Sample Output

Run `test_explainer.py` to invoke the service end-to-end against two local images:

```bash
uv run python test_explainer.py
```

`DiscrepancyExplainer.explain()` output for two images from different rooms:

```json
{
  "summary": "The live frame shows a completely different location and equipment setup compared to the benchmark. The benchmark displays a dark server rack with electronic equipment and a monitor, while the live frame shows a battery storage room with multiple rows of industrial battery banks in metal framework racks on a yellow-striped floor.",
  "possible_causes": [
    "Camera was physically relocated to a different room or facility",
    "Camera feed was switched to a different camera in the surveillance system",
    "Complete replacement or reconfiguration of the monitored area from IT equipment room to battery/power storage facility",
    "Wrong camera feed being displayed due to system configuration error or mislabeling"
  ],
  "comparison_notes": "The benchmark image shows a vertical server rack installation with dark colored equipment, electronic components, and a mounted display screen in what appears to be a data center or server room environment. The live frame depicts an entirely different space - a battery storage facility with horizontal rows of large red and black battery units housed in light blue/gray metal framework structures, positioned along a corridor with distinctive yellow safety striping on the floor. The lighting, spatial layout, equipment type, and environmental context are completely different between the two images."
}
```

## LLM Evaluation with Promptfoo

The `DiscrepancyExplainer` prompt is evaluated with [Promptfoo](https://promptfoo.dev) using known image pairs and structured assertions.

### Test Cases

| Test case | Discrepancy | Key assertions |
|---|---|---|
| Clear camera | None (control) | No obstruction, blur, or significant difference mentioned |
| Lens obstruction | Partial physical block | Mentions blocked region; suggests physical cause; contains "obstruct" |
| Blurry live frame | Loss of sharpness | Contrasts sharpness between images |
| Lighting change | Darker or overexposed | Mentions brightness/exposure; suggests environmental cause |
| Camera drift | Angle shifted from benchmark | Notes shift in perspective or composition |

### Running the Evaluation

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

## Security Considerations

- AWS credentials via environment variables (not hardcoded)
- `.env` file excluded from version control
- Input validation prevents path traversal
- File size limits prevent resource exhaustion
- Timeout handling prevents hanging requests

**Recommended for production**: Use AWS IAM roles instead of access keys; implement AWS Secrets Manager for credential storage.