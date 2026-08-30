import { useMemo } from "react";

export interface SegmentVerdict {
  segment_index: number;
  start_time: number;
  end_time: number;
  qr_detected: boolean;
  banking_context: number;
  crypto_context: number;
  transaction_likely: number;
  transaction_executed?: number;
  transaction_failed?: boolean;
  proof_frame?: string;
  ocr_text?: string;
}

export interface SummaryData {
  original_filename: string;
  segment_verdicts: SegmentVerdict[];
  final_summary?: any;
  betting_segment_scores?: number[];
  betting_transaction_attribution?: any[];
  crypto_betting_attribution?: any[];
  final_summary_txt?: string;
  final_verdict_report_txt?: string;
  metadata?: any;
}

export function useDashboardMetrics(summaryData: SummaryData | null) {
  return useMemo(() => {
    if (!summaryData) return null;

    const verdicts = summaryData.segment_verdicts || [];
    const betScores = summaryData.betting_segment_scores || [];
    const betTx = summaryData.betting_transaction_attribution || [];

    const segmentCount = verdicts.length;
    const totalDuration = verdicts.length > 0 ? verdicts[verdicts.length - 1].end_time : 0;

    const qrSegments = verdicts.filter(v => v.qr_detected);
    const bankingSegs = verdicts.filter(v => (v.banking_context || 0) > 30);
    const cryptoSegs = verdicts.filter(v => (v.crypto_context || 0) > 30);
    const txLikelySegs = verdicts.filter(v => (v.transaction_likely || 0) >= 50);
    const txExecSegs = verdicts.filter(v => (v.transaction_executed || 0) > 0);
    const txFailedSegs = verdicts.filter(v => v.transaction_failed);

    const nTxAtt = betTx.length;
    const nTxExec = txExecSegs.length;

    let failedTxRecords: any[] = [];
    let failedTxTimes: string[] = [];

    if (nTxAtt > 0 && nTxExec === 0) {
      failedTxRecords = betTx;
      failedTxTimes = betTx.map(t => t.transaction_time);
    }

    const bettingNonZero = betScores.filter(s => s > 0);
    const bettingPct = betScores.length ? Number(((bettingNonZero.length / betScores.length) * 100).toFixed(1)) : 0;
    const maxBetScore = betScores.length ? Math.max(...betScores) : 0;
    const avgBetScore = bettingNonZero.length ? Number((bettingNonZero.reduce((a, b) => a + b, 0) / bettingNonZero.length).toFixed(1)) : 0;

    return {
      segmentCount,
      totalDuration,
      qrSegments,
      bankingSegs,
      cryptoSegs,
      txLikelySegs,
      txExecSegs,
      txFailedSegs,
      nTxAtt,
      nTxExec,
      failedTxRecords,
      failedTxTimes,
      bettingNonZero,
      bettingPct,
      maxBetScore,
      avgBetScore,
      verdicts,
      betScores,
      betTx
    };
  }, [summaryData]);
}
