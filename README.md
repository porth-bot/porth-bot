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

[**porth-bot/grokking-transformer**](https://github.com/porth-bot/grokking-transformer) — a transformer written from the attention up, trained on modular arithmetic until it groks: memorizes the training set at step 100, sits near 20% test accuracy for ~1,300 steps (median over 5 seeds) with the training loss already flat, then jumps to 100%. The repo is about what *controls* that delay and what changes inside. Weight decay decides whether it happens at all (never at wd = 0, across all five seeds), data fraction decides when, and both sweeps carry median + IQR bands over seeds rather than a single lucky run. The mechanistic half reads the trained model directly: the embeddings bend into a ring, and a 2D Fourier transform of the logits shows the generalizing solution is a sparse sum over a handful of frequencies — 98% of the logit energy on the a+b diagonal, versus 12% at memorization. The circuit is measurably forming *underneath* the memorization, before the accuracy moves.

[**porth-bot/gp-from-scratch**](https://github.com/porth-bot/gp-from-scratch) — Gaussian process regression in pure NumPy: kernels with hand-derived, finite-difference-checked gradients, marginal-likelihood optimization, a calibration study, and a Mauna Loa CO₂ forecast — plus the neural-tangent-kernel correspondence, where a from-scratch wide ReLU network is measured converging to its analytic GP limit as width grows. Same rule as the rest of the series: every posterior cross-checked against scikit-learn, every gradient against central differences. Includes an honestly-reported negative result — ML-II raises the CO₂ evidence but extrapolates *worse* than the hand-set prior, and the writeup explains why.

[**porth-bot/pinn-from-scratch**](https://github.com/porth-bot/pinn-from-scratch) — physics-informed neural networks built from the derivatives up, in PyTorch. The PDE residual comes from exact autograd derivatives of the network (`u_t`, `u_x`, `u_xx` written out by hand), and every problem is measured against a ground truth that is never a grid solver: the heat equation against its exact Fourier series, Burgers' against the Cole-Hopf transform evaluated by Gauss-Hermite quadrature. The centerpiece is a failure mode, not a win — spectral bias measured across initial-condition frequencies k = 1…32, where the network fits k = 16 slowly and k = 32 not at all, explained by the NTK eigenspectrum that `gp-from-scratch` derives. The README leads with the honest part: on these problems classical solvers win, decisively.

Four repos, one rule: the core written out by hand, every non-obvious claim checked against a closed form or an independent oracle, and limitations stated rather than buried. They lean on each other where the math actually overlaps — the NTK derived in `gp-from-scratch` is what explains `pinn-from-scratch`'s spectral bias, and `mcmc-from-scratch` samples the finite-width weight posterior that the same NTK section solves in closed form at infinite width. Score-based diffusion is next.

---

## Also working on

- [**pinn-learning-journey**](https://github.com/porth-bot/pinn-learning-journey) — daily log of learning Physics-Informed Neural Networks from scratch. Theory, code, experiments. The goal is solving PDEs with neural networks well enough to use them on actual problems, not toy ones.
