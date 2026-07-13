import csvRaw from './ai_intelligence_growth.csv?raw';

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

function parseCsv(raw: string): AiIntelligenceRow[] {
    const lines = raw.trim().split(/\r?\n/);
    return lines.slice(1).map((line) => {
        const parts = line.split(',');
        return {
            year: Number(parts[0]),
            readingComprehension: Number(parts[1]),
            mathReasoning: Number(parts[2]),
            codeGeneration: Number(parts[3]),
            complexReasoningHumanityExam: Number(parts[4]),
        };
    });
}

export const AI_INTELLIGENCE_DATA: AiIntelligenceRow[] = parseCsv(csvRaw);

export function buildIntelligenceTrendOption(customData?: AiIntelligenceRow[], metricLabels?: Record<string, string>, abilityScoreLabel = '能力得分') {
    const data = customData || AI_INTELLIGENCE_DATA;
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

export function buildIntelligenceSummary2026() {
    const latest = AI_INTELLIGENCE_DATA[AI_INTELLIGENCE_DATA.length - 1];
    if (!latest) {
        return { reading: 0, math: 0, code: 0, complex: 0 };
    }
    return {
        reading: latest.readingComprehension,
        math: latest.mathReasoning,
        code: latest.codeGeneration,
        complex: latest.complexReasoningHumanityExam,
    };
}
