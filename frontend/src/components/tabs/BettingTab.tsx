import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ReactECharts from "echarts-for-react";

export function BettingTab({ metrics }: { metrics: any }) {
  if (!metrics) return null;

  const buildAreaChart = () => {
    const data = metrics.betScores.map((score: number, idx: number) => {
      const time = metrics.verdicts[idx]?.start_time || idx;
      return [time.toFixed(2), score];
    });

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => `Time: ${params[0].value[0]}s<br/>Betting Score: <b>${params[0].value[1].toFixed(1)}</b>`
      },
      grid: { left: 40, right: 20, top: 20, bottom: 40 },
      xAxis: { type: 'value', name: 'Time (s)', nameLocation: 'middle', nameGap: 25 },
      yAxis: { type: 'value', min: 0, max: 100 },
      series: [{
        type: 'line', data: data, smooth: true, symbol: 'none',
        areaStyle: {
          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(217,119,6,0.5)' }, { offset: 1, color: 'rgba(217,119,6,0)' }]
          }
        },
        lineStyle: { color: '#D97706', width: 2 },
        markLine: { silent: true, data: [{ yAxis: 50 }], lineStyle: { color: '#CBD5E1', type: 'dashed' } }
      }]
    };
  };

  const buildHeatmap = () => {
    const lanes = [
      { name: "Betting UI", data: metrics.betScores.map((s:any,i:any) => s > 50 ? metrics.verdicts[i] : null).filter(Boolean), color: "#D97706", laneIdx: 0 },
      { name: "Banking Context", data: metrics.bankingSegs, color: "#0891B2", laneIdx: 1 },
      { name: "Crypto Context", data: metrics.cryptoSegs, color: "#7C3AED", laneIdx: 2 },
      { name: "QR / Payment", data: metrics.qrSegments, color: "#F59E0B", laneIdx: 3 },
      { name: "High Tx Likelihood", data: metrics.txLikelySegs, color: "#DC2626", laneIdx: 4 },
    ];

    const allItems: any[] = [];
    lanes.forEach(lane => {
      lane.data.forEach((seg: any) => {
        if (!seg || !seg.end_time) return;
        allItems.push({
          value: [
            lane.laneIdx, seg.start_time, seg.end_time,
            `${lane.name}\nStart: ${seg.start_time.toFixed(2)}s | End: ${seg.end_time.toFixed(2)}s`
          ],
          itemStyle: { color: lane.color }
        });
      });
    });

    return {
      tooltip: { formatter: (params: any) => params.value[3].replace(/\n/g, '<br/>') },
      grid: { left: 140, right: 20, top: 10, bottom: 30 },
      xAxis: { type: 'value', min: 0, max: metrics.totalDuration },
      yAxis: { data: lanes.map(l => l.name), inverse: true, axisLine: { show: false }, axisTick: { show: false } },
      series: [{
        type: 'custom',
        renderItem: (params: any, api: any) => {
          const cat = api.value(0);
          const start = api.coord([api.value(1), cat]);
          const end = api.coord([api.value(2), cat]);
          const height = api.size([0, 1])[1] * 0.6;
          return { type: 'rect', shape: { x: start[0], y: start[1]-height/2, width: Math.max(end[0]-start[0],3), height }, style: api.style() };
        },
        encode: { x: [1, 2], y: 0 }, data: allItems
      }]
    };
  };

  const getBettingRuns = () => {
    const runs = [];
    let start = null;
    for (let i = 0; i < metrics.betScores.length; i++) {
      if (metrics.betScores[i] > 0 && start === null) start = i;
      else if (metrics.betScores[i] === 0 && start !== null) { runs.push([start + 1, i, i - start]); start = null; }
    }
    if (start !== null) runs.push([start + 1, metrics.betScores.length, metrics.betScores.length - start]);
    return runs.sort((a, b) => b[2] - a[2]).slice(0, 10);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Betting Confidence Trend</CardTitle>
          <p className="text-xs text-slate-500">Smooth area chart — betting evidence signal strength across the full video.</p>
        </CardHeader>
        <CardContent>
          <ReactECharts option={buildAreaChart()} style={{ height: '300px', width: '100%' }} />
          <div className="grid grid-cols-4 gap-4 mt-4">
            <div className="text-center"><div className="text-xl font-bold">{metrics.bettingNonZero.length}</div><div className="text-xs text-slate-500">Segments w/ Betting</div></div>
            <div className="text-center"><div className="text-xl font-bold">{metrics.bettingPct}%</div><div className="text-xs text-slate-500">Coverage</div></div>
            <div className="text-center"><div className="text-xl font-bold">{metrics.maxBetScore.toFixed(1)}</div><div className="text-xs text-slate-500">Max Score</div></div>
            <div className="text-center"><div className="text-xl font-bold">{metrics.avgBetScore.toFixed(1)}</div><div className="text-xs text-slate-500">Avg Score</div></div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Video Activity Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          <ReactECharts option={buildHeatmap()} style={{ height: '300px', width: '100%' }} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-sm">Continuous Betting Runs</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {getBettingRuns().map((run, i) => {
              const startSeg = metrics.verdicts[run[0] - 1];
              const endSeg = metrics.verdicts[run[1] - 1] || metrics.verdicts[metrics.verdicts.length - 1];
              const dur = endSeg && startSeg ? (endSeg.end_time - startSeg.start_time).toFixed(1) : 0;
              return (
                <div key={i} className="flex justify-between items-center p-2 bg-slate-50 border border-slate-100 rounded text-sm">
                  <span className="font-mono text-slate-500">#{run[0]}-{run[1]}</span>
                  <span className="text-xs text-slate-400">{startSeg?.start_time?.toFixed(1)}s - {endSeg?.end_time?.toFixed(1)}s</span>
                  <span className="bg-amber-100 text-amber-800 text-xs px-2 py-1 rounded font-bold">{dur}s dur ({run[2]} segs)</span>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Transaction Attribution</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {metrics.betTx.map((tx: any, i: number) => {
              const score = tx.evidence?.final_score || tx.betting_purpose_score || 0;
              const attributed = tx.transaction_used_for_betting;
              return (
                <div key={i} className="p-2 border rounded text-sm flex flex-col gap-1">
                  <div className="flex justify-between">
                    <span className="font-bold">Seg {tx.segment_index}</span>
                    <span className="font-mono text-xs">{tx.transaction_time}</span>
                  </div>
                  <div className="flex justify-between items-center mt-1">
                    <span className="text-slate-500 text-xs">Score: {score.toFixed(1)} | Conf: {tx.confidence.toFixed(0)}%</span>
                    <span className={`text-[10px] px-2 py-1 rounded-full font-bold ${attributed ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}`}>
                      {attributed ? 'ATTRIBUTED' : 'NOT ATTRIBUTED'}
                    </span>
                  </div>
                </div>
              );
            })}
            {metrics.betTx.length === 0 && <div className="text-slate-500 italic text-sm">No betting transactions detected.</div>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
