# Parth Rana

Student. Building things in applied ML — mostly around perception, detection, and learning physical systems from data.

---

## Currently building: DeepScope

[**porth-bot/deepscope**](https://github.com/porth-bot/deepscope) — a deepfake detection platform.

Most deepfake detectors I tried fell into one of two traps: a single model that's confident about everything (including the things it gets wrong), or a brittle pipeline that works on one face shape and one lighting condition. I wanted something that admits uncertainty out loud and breaks down *why* it thinks an image is fake — not just a score.

### What it does

You hand it an image or a video. It returns a confidence score, a set of component scores, an adversarial analysis, and — for video — temporal consistency metrics across frames. The frontend shows the decomposition so the verdict isn't a black box.

### How it's put together

- **Three detectors, weighted ensemble.** CLIP (semantic mismatch), EfficientNet (texture artifacts), and a feature-fusion model (low-level statistics). Default weights are 0.5 / 0.3 / 0.2 — tuned, not arbitrary. Each one fails in a different way, which is the point.
- **Apple Silicon Core ML.** Models run on the Neural Engine when available. Lazy-loaded with LRU eviction so the API can hold the working set in memory and evict the rest. First request triggers load; production warms on startup.
- **Temporal consistency for video.** Optical flow across sampled frames catches the class of fakes where each individual frame looks plausible but the motion between them doesn't.
- **A face-only image corpus.** Earlier iterations were too generous — the dataset included scenes where face artifacts were a small fraction of the pixels. Replaced with StyleGAN2 portraits and public-domain photographs. Detection on the held-out set went from inconsistent to 75% at the default threshold, tunable higher.
- **Explainability.** Grad-CAM heatmaps overlaid on the input. Optional per-request — they're expensive — but on by default in dev.

### Stack

FastAPI (async, Python 3.13) with Redis caching and a memory-cache fallback for when Redis isn't reachable. MinIO/S3 for artifacts, Postgres for results, Prometheus for metrics. Next.js 14 (App Router) on the frontend, Zustand for state, a single axios client with request-ID propagation end to end. Docker Compose for the full stack; a dev stack with pgAdmin, MailHog, and Redis Commander.

### What was hard

The fun parts:

- **Calibrating the ensemble.** Each detector has its own confidence distribution. Naive averaging gave one model implicit veto power. The weighting is a compromise — CLIP catches the "this face doesn't belong in this scene" failures the texture models miss, but texture models catch GAN fingerprints CLIP shrugs at.
- **Knowing when to say "I don't know."** The system is allowed to return low confidence. A lot of detection literature treats that as failure; I think it's the only honest output for ambiguous frames.
- **Video without exploding the API.** Frame sampling, parallel detector calls, streaming results back over WebSocket. The 5-minute frontend timeout on video uploads exists because reality is messier than the design doc.

### What's next

- More robust face-swap detection (the current weakness is video face swaps with good temporal coherence).
- Better calibration so the confidence score means the same thing across image and video paths.
- A public demo, once I'm confident enough in the false-positive rate to put it in front of anyone.

---

## From-scratch ML foundations

[**porth-bot/mcmc-from-scratch**](https://github.com/porth-bot/mcmc-from-scratch) — Metropolis–Hastings, Gibbs, and Hamiltonian Monte Carlo in pure NumPy. The rule for the whole repo: no claim without a ground truth or a cross-check. Hand-derived gradients are tested against finite differences, sampler moments against closed-form posteriors, the ESS estimator against an AR(1) closed form — and there's a Neal's-funnel experiment where R-hat says "converged" while the sampler is measurably biased, plus the reparameterization that actually fixes it. Full derivations live in the repo (`theory/derivations.md`), CI-tested.

First in a series of from-scratch builds under the same rule. Next up: transformer grokking, Gaussian processes, physics-informed neural nets.

---

## Also working on

- [**pinn-learning-journey**](https://github.com/porth-bot/pinn-learning-journey) — daily log of learning Physics-Informed Neural Networks from scratch. Theory, code, experiments. The goal is solving PDEs with neural networks well enough to use them on actual problems, not toy ones.

---

## Reach me

- Email: ai.automate101 at gmail dot com
