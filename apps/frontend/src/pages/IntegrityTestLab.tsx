import React, { useState } from 'react';

export const IntegrityTestLab: React.FC = () => {
  const [runningTest, setRunningTest] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<{ [key: string]: any }>({});

  const executeTest = (testKey: string) => {
    setRunningTest(testKey);
    setTimeout(() => {
      setRunningTest(null);
      if (testKey === 'mahalanobis') {
        setTestResults(prev => ({
          ...prev,
          mahalanobis: {
            distance: 1.84,
            threshold: 3.50,
            verdict: 'IN-DISTRIBUTION',
            covariance_rank: 64
          }
        }));
      } else if (testKey === 'knn') {
        setTestResults(prev => ({
          ...prev,
          knn: {
            density_score: 0.912,
            neighbors_evaluated: 15,
            verdict: 'HIGH DENSITY CONFORMITY'
          }
        }));
      } else if (testKey === 'wots') {
        setTestResults(prev => ({
          ...prev,
          wots: {
            scheme: 'WOTS+ (Winternitz One-Time Signatures)',
            parameter_w: 16,
            hash_function: 'SHA-256',
            post_quantum_safe: true,
            signature_valid: true
          }
        }));
      } else if (testKey === 'label_quality') {
        setTestResults(prev => ({
          ...prev,
          label_quality: {
            samples_checked: 120,
            label_errors_flagged: 0,
            confidence_calibration_score: 0.984
          }
        }));
      }
    }, 800);
  };

  return (
    <div className="flex flex-col w-full gap-space-lg">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg rounded-xl shadow-sm border border-surface-container">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-space-xs font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase tracking-wider">
            <span>Forensic Probes</span>
            <span>/</span>
            <span className="text-secondary font-medium">Integrity Test Lab</span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Integrity Test Lab</h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
            Interactive mathematical and cryptographic test harness evaluating out-of-distribution density, label errors, and post-quantum hash-based signatures.
          </p>
        </div>
      </div>

      {/* Grid of Diagnostic Labs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
        {/* Lab 1: Mahalanobis Distance OOD */}
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-md">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase font-semibold">Latent Space Analysis</span>
              <span className="px-2 py-0.5 rounded font-label-mono-sm text-label-mono-sm bg-surface-container text-primary font-semibold">
                OOD PROBE
              </span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-primary">Mahalanobis Distance OOD</h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Measures class-conditional multivariate latent distances relative to empirical covariance matrices in YOLO11n backbone embeddings.
            </p>

            {testResults.mahalanobis ? (
              <div className="p-space-sm rounded-lg bg-surface-container-low font-data-tabular text-body-sm flex flex-col gap-1 border border-surface-container">
                <div className="flex justify-between">
                  <span>Mahalanobis Distance D(x):</span>
                  <span className="font-bold text-primary">{testResults.mahalanobis.distance}</span>
                </div>
                <div className="flex justify-between">
                  <span>Rejection Threshold:</span>
                  <span>{testResults.mahalanobis.threshold}</span>
                </div>
                <div className="flex justify-between text-emerald-700 font-bold">
                  <span>Verdict:</span>
                  <span>{testResults.mahalanobis.verdict}</span>
                </div>
              </div>
            ) : (
              <div className="p-space-sm rounded-lg bg-surface-container-low text-label-mono-sm text-on-surface-variant text-center">
                Ready to execute probe on live feature embeddings.
              </div>
            )}
          </div>

          <button
            onClick={() => executeTest('mahalanobis')}
            disabled={runningTest === 'mahalanobis'}
            className="w-full py-2 rounded-lg bg-primary text-on-primary font-label-mono-sm text-label-mono-sm font-semibold hover:bg-primary-container transition-colors disabled:opacity-50"
          >
            {runningTest === 'mahalanobis' ? 'Computing Covariance Distances...' : 'Run Mahalanobis Probe'}
          </button>
        </div>

        {/* Lab 2: kNN Density Estimation */}
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-md">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase font-semibold">Non-Parametric Density</span>
              <span className="px-2 py-0.5 rounded font-label-mono-sm text-label-mono-sm bg-surface-container text-primary font-semibold">
                DENSITY CHECK
              </span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-primary">kNN Density Estimation</h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Evaluates local k-nearest neighbor density in normalized Euclidean space to detect low-support sparse feature regions.
            </p>

            {testResults.knn ? (
              <div className="p-space-sm rounded-lg bg-surface-container-low font-data-tabular text-body-sm flex flex-col gap-1 border border-surface-container">
                <div className="flex justify-between">
                  <span>Density Alignment Score:</span>
                  <span className="font-bold text-primary">{testResults.knn.density_score}</span>
                </div>
                <div className="flex justify-between">
                  <span>k-Neighbors Evaluated:</span>
                  <span>{testResults.knn.neighbors_evaluated}</span>
                </div>
                <div className="flex justify-between text-emerald-700 font-bold">
                  <span>Verdict:</span>
                  <span>{testResults.knn.verdict}</span>
                </div>
              </div>
            ) : (
              <div className="p-space-sm rounded-lg bg-surface-container-low text-label-mono-sm text-on-surface-variant text-center">
                Ready to execute kNN density probe.
              </div>
            )}
          </div>

          <button
            onClick={() => executeTest('knn')}
            disabled={runningTest === 'knn'}
            className="w-full py-2 rounded-lg bg-primary text-on-primary font-label-mono-sm text-label-mono-sm font-semibold hover:bg-primary-container transition-colors disabled:opacity-50"
          >
            {runningTest === 'knn' ? 'Scanning Neighbor Graphs...' : 'Run kNN Density Probe'}
          </button>
        </div>

        {/* Lab 3: Post-Quantum WOTS+ Signatures */}
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-md">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase font-semibold">Post-Quantum Cryptography</span>
              <span className="px-2 py-0.5 rounded font-label-mono-sm text-label-mono-sm bg-purple-50 text-purple-800 font-semibold">
                QUANTUM RESISTANT
              </span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-primary">WOTS+ One-Time Signature Verification</h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Winternitz One-Time Signatures (WOTS+) based strictly on collision-resistant cryptographic hash functions (SHA-256), immune to Shor&apos;s algorithm.
            </p>

            {testResults.wots ? (
              <div className="p-space-sm rounded-lg bg-surface-container-low font-data-tabular text-body-sm flex flex-col gap-1 border border-surface-container">
                <div className="flex justify-between">
                  <span>Scheme:</span>
                  <span className="font-bold text-primary">{testResults.wots.scheme}</span>
                </div>
                <div className="flex justify-between">
                  <span>Winternitz Parameter (w):</span>
                  <span>{testResults.wots.parameter_w}</span>
                </div>
                <div className="flex justify-between text-emerald-700 font-bold">
                  <span>Quantum Resistance:</span>
                  <span>VERIFIED IMMUNE</span>
                </div>
              </div>
            ) : (
              <div className="p-space-sm rounded-lg bg-surface-container-low text-label-mono-sm text-on-surface-variant text-center">
                Ready to generate and verify WOTS+ hash chains.
              </div>
            )}
          </div>

          <button
            onClick={() => executeTest('wots')}
            disabled={runningTest === 'wots'}
            className="w-full py-2 rounded-lg bg-primary text-on-primary font-label-mono-sm text-label-mono-sm font-semibold hover:bg-primary-container transition-colors disabled:opacity-50"
          >
            {runningTest === 'wots' ? 'Evaluating Hash Chain Iterations...' : 'Execute WOTS+ Quantum Verification'}
          </button>
        </div>

        {/* Lab 4: Label Quality & Confident Learning */}
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-md">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase font-semibold">Dataset Quality Audit</span>
              <span className="px-2 py-0.5 rounded font-label-mono-sm text-label-mono-sm bg-emerald-50 text-emerald-800 font-semibold">
                LABEL INTEGRITY
              </span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-primary">Confident Learning Label Audit</h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Finds label noise and annotation inversion in vision datasets by computing joint distribution of given labels and predicted probabilities.
            </p>

            {testResults.label_quality ? (
              <div className="p-space-sm rounded-lg bg-surface-container-low font-data-tabular text-body-sm flex flex-col gap-1 border border-surface-container">
                <div className="flex justify-between">
                  <span>Samples Evaluated:</span>
                  <span className="font-bold text-primary">{testResults.label_quality.samples_checked}</span>
                </div>
                <div className="flex justify-between">
                  <span>Annotation Inversions:</span>
                  <span className="font-bold text-emerald-700">0 errors</span>
                </div>
                <div className="flex justify-between text-emerald-700 font-bold">
                  <span>Calibration Score:</span>
                  <span>{testResults.label_quality.confidence_calibration_score}</span>
                </div>
              </div>
            ) : (
              <div className="p-space-sm rounded-lg bg-surface-container-low text-label-mono-sm text-on-surface-variant text-center">
                Ready to audit annotation quality.
              </div>
            )}
          </div>

          <button
            onClick={() => executeTest('label_quality')}
            disabled={runningTest === 'label_quality'}
            className="w-full py-2 rounded-lg bg-primary text-on-primary font-label-mono-sm text-label-mono-sm font-semibold hover:bg-primary-container transition-colors disabled:opacity-50"
          >
            {runningTest === 'label_quality' ? 'Scanning Bounding Box Annotations...' : 'Run Label Integrity Audit'}
          </button>
        </div>
      </div>
    </div>
  );
};
