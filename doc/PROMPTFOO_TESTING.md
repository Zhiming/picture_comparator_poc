# LLM Testing with Promptfoo

Promptfoo is an open-source framework for evaluating LLM outputs. This document explains how to use it to test image description tasks — where an LLM looks at an image and explains what it contains — and verify the response against a reference answer.

---

## How it works

```
test image + prompt --> [LLM provider] --> description response --> [assert vs reference answer]
```

You define:
- A **prompt** (what to ask the LLM about the image)
- **Test cases** (image + reference answer pairs)
- **Assertions** (how to compare LLM response to reference)

Promptfoo runs each test, calls the LLM, and scores the results.

---

## Installation

```bash
npm install -g promptfoo
# or run without installing:
npx promptfoo
```

---

## File structure

```
project/
  promptfooconfig.yaml    # main config
  prompt.json             # multimodal prompt template
  images/
    test1.jpg
    test2.jpg
```

---

## Step 1 — Define the prompt

Because the prompt includes an image (multimodal), it must be a JSON file rather than inline YAML.

**`prompt.json`**

```json
[
  {
    "role": "user",
    "content": [
      {
        "type": "text",
        "text": "Look at this image and explain what it is about. Be specific and descriptive."
      },
      {
        "type": "image",
        "source": {
          "type": "base64",
          "media_type": "image/jpeg",
          "data": "{{image}}"
        }
      }
    ]
  }
]
```

`{{image}}` is a variable — Promptfoo substitutes it with base64 image data from each test case.

---

## Step 2 — Write the config

**`promptfooconfig.yaml`**

```yaml
prompts:
  - file://prompt.json

providers:
  - anthropic:messages:claude-sonnet-4-6

tests:
  - description: "Highway traffic camera"
    vars:
      image: "file://images/test1.jpg"
    assert:
      - type: factuality
        value: "The image shows a highway with cars and trucks in traffic"

  - description: "Blurry obstructed camera"
    vars:
      image: "file://images/test2.jpg"
    assert:
      - type: factuality
        value: "The image is blurry or obstructed with poor visibility"
      - type: llm-rubric
        value: "Response mentions blur, obstruction, or degraded image quality"

  - description: "Empty parking lot at night"
    vars:
      image: "file://images/test3.jpg"
    assert:
      - type: factuality
        value: "The image shows an empty parking lot at night with artificial lighting"
      - type: similar
        value: "An empty car park with no vehicles, taken at night"
        threshold: 0.75
```

Promptfoo automatically reads each `file://images/*.jpg` and encodes it as base64 before injecting it into the prompt.

---

## Step 3 — Set up credentials

Create a `.env` file in the same directory:

```
ANTHROPIC_API_KEY=your_api_key_here
```

Promptfoo loads `.env` automatically.

---

## Step 4 — Run the evaluation

```bash
# Run all tests
npx promptfoo eval

# Open results in browser UI
npx promptfoo view
```

---

## Assertion types explained

### `factuality` — semantic fact-checking (recommended)

Uses an LLM grader to check whether the response is factually consistent with your reference answer. Handles paraphrasing and different wording — it does not require an exact match.

```yaml
assert:
  - type: factuality
    value: "The image shows a busy intersection with pedestrians and vehicles"
```

**Best for**: Verifying the LLM captured the correct content of the image.

---

### `llm-rubric` — criteria-based grading

You write a grading rule in plain English. The grader LLM checks whether the response satisfies it.

```yaml
assert:
  - type: llm-rubric
    value: "Response describes the number of people visible in the image"
```

**Best for**: Checking that specific details or concepts are mentioned, beyond just factual consistency.

---

### `similar` — embedding cosine similarity

Computes semantic similarity between the LLM response and your reference using text embeddings. Returns a score from 0.0 to 1.0 and passes if it meets the threshold.

```yaml
assert:
  - type: similar
    value: "A crowded street market with food stalls"
    threshold: 0.8
```

**Best for**: Checking overall semantic closeness when you have a well-written reference description.

---

### `contains` — substring match

Checks whether the response contains a specific string. Deterministic and fast, no LLM grader needed.

```yaml
assert:
  - type: contains
    value: "highway"
```

**Best for**: Verifying that key terms or labels appear in the response.

---

## Combining assertions

You can stack multiple assertions on a single test for stricter checking:

```yaml
- description: "Traffic camera with obstruction"
  vars:
    image: "file://images/obstructed.jpg"
  assert:
    - type: factuality
      value: "The camera view is partially blocked by an object"
    - type: llm-rubric
      value: "Response identifies that the image quality is poor or the view is obstructed"
    - type: contains
      value: "obstruct"
```

All assertions must pass for the test to pass.

---

## Testing multiple providers side by side

You can compare different models on the same test cases:

```yaml
providers:
  - anthropic:messages:claude-sonnet-4-6
  - anthropic:messages:claude-haiku-4-5-20251001
  - openai:gpt-4o
```

Promptfoo runs every test against every provider and shows a comparison table in the UI.

---

## Using AWS Bedrock instead of Anthropic directly

If you want to use AWS Bedrock (as the main project does), replace the provider:

```yaml
providers:
  - id: bedrock:anthropic.claude-3-5-sonnet-20241022-v2:0
    config:
      region: us-east-1
```

Set AWS credentials in your environment or `.env`:

```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

---

## Interpreting results

After running `npx promptfoo eval`, the terminal shows a summary table:

```
+-----------------------------------+----------+--------+
| Test                              | Provider | Pass   |
+-----------------------------------+----------+--------+
| Highway traffic camera            | claude   | PASS   |
| Blurry obstructed camera          | claude   | FAIL   |
| Empty parking lot at night        | claude   | PASS   |
+-----------------------------------+----------+--------+
2/3 tests passed (66.7%)
```

Run `npx promptfoo view` for a full browser UI with:
- The actual LLM response for each test
- Which assertions passed or failed and why
- Side-by-side comparison across providers

---

## Assertion type summary

| Type          | How it compares                        | Requires LLM grader | Best for                          |
|---------------|----------------------------------------|---------------------|-----------------------------------|
| `factuality`  | Semantic consistency with reference    | Yes                 | Core content verification         |
| `llm-rubric`  | Custom criteria in plain English       | Yes                 | Specific detail or concept checks |
| `similar`     | Embedding cosine similarity + threshold| No (embeddings)     | Overall semantic closeness        |
| `contains`    | Exact substring match                  | No                  | Key term presence                 |
| `equals`      | Exact string match                     | No                  | Structured / JSON output checks   |
