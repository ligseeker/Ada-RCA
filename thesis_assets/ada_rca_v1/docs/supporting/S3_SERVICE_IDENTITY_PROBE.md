# S3 Service-Identity Diagnostic Probe

Status: COMPLETE; diagnostic only; no RCA gate  
Generating source commit: `88e3dcf726e14256013b989add8d6fbc5183dc74`

S3 predicts candidate service identity from the exact frozen S2 16D
pre-event-only representation. Every event remains wholly within one frozen
OOF fold, and the scaler is fit on training rows only. The fixed model is
`sklearn.linear_model.LogisticRegression(penalty="l2", C=1.0,
solver="lbfgs", max_iter=5000, class_weight=None, fit_intercept=True)` under
scikit-learn 1.2.1.

| Dataset | Classes | Top-1 accuracy | Macro-F1 | Uniform reference | Majority reference |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 11 | 0.598990 | 0.583065 | 0.090909 | 0.090909 |
| RE2-TT | 68 | 0.132190 | 0.113494 | 0.014706 | 0.014706 |

Each service occurs equally often in the candidate rows (90 rows per service),
so empirical majority equals the uniform reference in these artifacts. Fold
event counts are 60 train / 30 test for each of the three folds.

Interpretation is deliberately limited: pre-event rows contain a strong
service-identifiable fingerprint on OB and a weaker but above-reference signal
on TT. This is evidence about stable service fingerprinting. It is not evidence
of root-label leakage, and S3 is not an RCA baseline or a final-method gate.
No post-result weak/moderate/strong thresholds were invented.

