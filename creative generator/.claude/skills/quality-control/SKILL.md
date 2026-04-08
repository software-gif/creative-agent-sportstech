# Quality Control Agent

> Auto-reviews generated lifestyle images before they appear on the board. Checks product accuracy, pose correctness, direction, and overall quality. Flags issues and assigns a quality score.

## Problem
Not every generated image is usable. Common issues: wrong product design, person facing wrong direction, unnatural poses, distorted proportions. Manual review is slow. The QC Agent automates this — like Uni One's auto-evaluation system.

## How It Works
1. Takes a generated creative image (from Supabase or local path)
2. Loads the product reference images for comparison
3. Sends both to Gemini text model for analysis
4. Checks against product_knowledge.json rules (must_match, must_avoid)
5. Returns a quality score (1-10) and list of issues found
6. Updates the creative record in Supabase with QC results

## What Gets Checked
- **Product Accuracy** — Does the product match reference images?
- **Product Direction** — Is the display/console in the correct position?
- **Person Direction** — Is the person facing the right way?
- **Pose Correctness** — Natural body mechanics, feet on equipment, realistic weight distribution
- **Branding** — Is SPORTSTECH text visible and correct?
- **Environment Quality** — Does the room look realistic?
- **Technical Quality** — Any AI artifacts, distortions, impossible geometry?

## Quality Scores
- **8-10**: Ready for use — product accurate, pose natural, high quality
- **5-7**: Usable with reservations — minor issues
- **1-4**: Rejected — significant product/pose/quality issues

## Usage
```bash
# Review a single creative by short_id
python3 .claude/skills/quality-control/scripts/main.py --creative CR-0015

# Review all unreviewed creatives
python3 .claude/skills/quality-control/scripts/main.py --review-all

# Review latest batch
python3 .claude/skills/quality-control/scripts/main.py --batch <batch_id>
```

## Output
- Updates creative record with: `rating` (1-10), `notes` (issues found)
- Console output with pass/fail for each creative
- Creatives below threshold can be auto-hidden or flagged

## Trigger
Run after generating a batch of creatives, or set up as automatic post-generation step.
