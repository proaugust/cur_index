export interface AiIntelligenceRow {
    year: number;
    readingComprehension: number;
    mathReasoning: number;
    codeGeneration: number;
    complexReasoningHumanityExam: number;
}

const METRIC_LABELS: Record<string, string> = {
    readingComprehension: '阅读理解',
    mathReasoning: '数学推理',
    codeGeneration: '代码生成',
    complexReasoningHumanityExam: '复杂推理（人类考试）',
};

const METRIC_COLORS = ['#2d8cf0', '#f25e43', '#64d572', '#9b59b6'];

const METRIC_KEYS = [
    'readingComprehension',
    'mathReasoning',
    'codeGeneration',
    'complexReasoningHumanityExam',
] as const;

export function buildIntelligenceTrendOption(
    customData?: AiIntelligenceRow[],
    metricLabels?: Record<string, string>,
    abilityScoreLabel = '能力得分',
) {
    const data = customData ?? [];
    const labels = metricLabels ?? METRIC_LABELS;
    const years = data.map((row) => String(row.year));

    return {
        tooltip: {
            trigger: 'axis',
        },
        legend: {
            top: 0,
            data: METRIC_KEYS.map((key) => labels[key]),
        },
        grid: {
            top: '14%',
            left: '2%',
            right: '3%',
            bottom: '2%',
            containLabel: true,
        },
        color: METRIC_COLORS,
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: years,
        },
        yAxis: {
            type: 'value',
            name: abilityScoreLabel,
            min: 0,
            max: 120,
        },
        series: METRIC_KEYS.map((key) => ({
            name: labels[key],
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            showSymbol: true,
            emphasis: { focus: 'series' },
            data: data.map((row) => row[key]),
        })),
    };
}
