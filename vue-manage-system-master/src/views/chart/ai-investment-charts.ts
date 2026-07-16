import {
    type AiTrendRow,
    type DashboardChartTexts,
    COUNTRY_COLORS,
} from './ai-index-data';

/** 年份色（当年投资图）：按时间轴索引取色，与国色分离 */
const YEAR_COLORS = [
    '#5470c6',
    '#91cc75',
    '#fac858',
    '#ee6666',
    '#73c0de',
    '#3ba272',
    '#fc8452',
    '#9a60b4',
    '#ea7ccc',
    '#48b8d0',
];

function hasInvestment(row: AiTrendRow): boolean {
    return row.investmentBillionsUsd != null && !Number.isNaN(row.investmentBillionsUsd);
}

function getInvestmentYears(data: AiTrendRow[]): number[] {
    return [...new Set(data.filter(hasInvestment).map((row) => row.year))].sort((a, b) => a - b);
}

function rowsByYear(data: AiTrendRow[], year: number): AiTrendRow[] {
    return data.filter((row) => row.year === year);
}

function countryColor(data: AiTrendRow[], country: string): string {
    const latestYear = Math.max(...data.map((row) => row.year));
    const countries = data
        .filter((row) => row.year === latestYear)
        .sort((a, b) => b.aiIndexScore - a.aiIndexScore)
        .map((row) => row.country);
    const index = countries.indexOf(country);
    return COUNTRY_COLORS[index >= 0 ? index : 0] ?? '#2d8cf0';
}

function yearColor(years: number[], year: number): string {
    const index = years.indexOf(year);
    return YEAR_COLORS[index >= 0 ? index % YEAR_COLORS.length : 0] ?? '#5470c6';
}

/** 按国对有值年份做跨年累加；无投资的年份保持 null */
export function toCumulativeInvestment(data: AiTrendRow[]): AiTrendRow[] {
    const byCountry = new Map<string, AiTrendRow[]>();
    for (const row of data) {
        const list = byCountry.get(row.country);
        if (list) list.push(row);
        else byCountry.set(row.country, [row]);
    }

    const result: AiTrendRow[] = [];
    for (const rows of byCountry.values()) {
        let sum = 0;
        for (const row of [...rows].sort((a, b) => a.year - b.year)) {
            const copy = { ...row };
            if (hasInvestment(row)) {
                sum += row.investmentBillionsUsd as number;
                copy.investmentBillionsUsd = Math.round(sum * 100) / 100;
            }
            result.push(copy);
        }
    }
    return result;
}

function buildBarRaceBase(
    years: number[],
    maxInvestment: number,
    axisName: string,
    texts: DashboardChartTexts,
    buildFrame: (year: number) => object,
) {
    return {
        baseOption: {
            timeline: {
                axisType: 'category',
                autoPlay: true,
                playInterval: 1200,
                data: years,
                label: {
                    formatter: (value: string) => `${value}${texts.yearSuffix}`,
                },
                left: '3%',
                right: '3%',
                bottom: 0,
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                valueFormatter: (value: number) => `${value} ${texts.investmentBillion}`,
            },
            grid: {
                top: '6%',
                left: '3%',
                right: '12%',
                bottom: '14%',
                containLabel: true,
            },
            xAxis: {
                type: 'value',
                max: maxInvestment,
                name: axisName,
            },
            yAxis: {
                type: 'category',
                inverse: true,
                animationDuration: 300,
                animationDurationUpdate: 300,
            },
            series: [
                {
                    type: 'bar',
                    realtimeSort: true,
                    seriesLayoutBy: 'column',
                },
            ],
            animationDuration: 0,
            animationDurationUpdate: 800,
            animationEasing: 'linear',
            animationEasingUpdate: 'linear',
        },
        options: years.map((year) => buildFrame(year)),
    };
}

/** 国色 + 跨年累计投资动态排行 */
export function buildInvestmentBarRaceOption(
    customData?: AiTrendRow[],
    texts: DashboardChartTexts = {
        countryLabel: (c) => c,
        aiIndex: 'AI 指数',
        investmentBillion: '十亿美元',
        investmentAxis: '累计投资 (十亿美元)',
        yearSuffix: ' 年',
        othersRegion: '其他地区',
        mapHigh: '高',
        mapLow: '低',
        noData: '暂无数据',
        formatTooltipIndex: (s) => `AI 指数：${s}`,
        formatTooltipInvestment: (v) => `累计投资：${v} 十亿美元`,
        formatTooltipPapers: (v) => `论文：${v} 千篇`,
    },
) {
    const annual = customData ?? [];
    const data = toCumulativeInvestment(annual);
    const years = getInvestmentYears(data);
    const invValues = data.filter(hasInvestment).map((row) => row.investmentBillionsUsd as number);
    const maxInvestment = invValues.length ? Math.ceil(Math.max(...invValues) * 1.1) : 1;
    const axisName = texts.investmentAxisCumulative ?? texts.investmentAxis;

    const buildFrame = (year: number) => {
        const ranked = [...rowsByYear(data, year)]
            .filter(hasInvestment)
            .sort((a, b) => (a.investmentBillionsUsd as number) - (b.investmentBillionsUsd as number));

        return {
            yAxis: {
                type: 'category',
                inverse: true,
                data: ranked.map((row) => texts.countryLabel(row.country)),
                animationDuration: 300,
                animationDurationUpdate: 300,
                max: 13,
            },
            series: [
                {
                    realtimeSort: true,
                    type: 'bar',
                    data: ranked.map((row) => {
                        const annualRow = rowsByYear(annual, year).find((item) => item.country === row.country);
                        const yearAdd =
                            annualRow && hasInvestment(annualRow)
                                ? (annualRow.investmentBillionsUsd as number)
                                : 0;
                        return {
                            value: row.investmentBillionsUsd,
                            itemStyle: { color: countryColor(annual, row.country) },
                            yearAdd,
                        };
                    }),
                    label: {
                        show: true,
                        position: 'right',
                        valueAnimation: true,
                        formatter: '{c} B',
                    },
                },
            ],
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: (params: unknown) => {
                    const list = Array.isArray(params) ? params : [params];
                    const first = list[0] as {
                        name?: string;
                        value?: number;
                        data?: { yearAdd?: number };
                    };
                    const cum = Number(first?.value ?? 0);
                    const add = Number(first?.data?.yearAdd ?? 0);
                    if (texts.formatTooltipCumulative) {
                        return `${first?.name ?? ''}<br/>${texts.formatTooltipCumulative(cum, add)}`;
                    }
                    return `${first?.name ?? ''}<br/>累计：${cum} ${texts.investmentBillion}（本年 +${add}）`;
                },
            },
        };
    };

    return buildBarRaceBase(years, maxInvestment, axisName, texts, buildFrame);
}

/** 年色 + 当年投资动态排行（颜色表示当前年份，国名认国家） */
export function buildAnnualInvestmentBarRaceOption(
    customData?: AiTrendRow[],
    texts: DashboardChartTexts = {
        countryLabel: (c) => c,
        aiIndex: 'AI 指数',
        investmentBillion: '十亿美元',
        investmentAxis: '当年投资 (十亿美元)',
        yearSuffix: ' 年',
        othersRegion: '其他地区',
        mapHigh: '高',
        mapLow: '低',
        noData: '暂无数据',
        formatTooltipIndex: (s) => `AI 指数：${s}`,
        formatTooltipInvestment: (v) => `当年投资：${v} 十亿美元`,
        formatTooltipPapers: (v) => `论文：${v} 千篇`,
    },
) {
    const data = customData ?? [];
    const years = getInvestmentYears(data);
    const invValues = data.filter(hasInvestment).map((row) => row.investmentBillionsUsd as number);
    const maxInvestment = invValues.length ? Math.ceil(Math.max(...invValues) * 1.1) : 1;
    const axisName = texts.investmentAxisAnnual ?? texts.investmentAxis;

    const buildFrame = (year: number) => {
        const color = yearColor(years, year);
        const ranked = [...rowsByYear(data, year)]
            .filter(hasInvestment)
            .sort((a, b) => (a.investmentBillionsUsd as number) - (b.investmentBillionsUsd as number));

        return {
            yAxis: {
                type: 'category',
                inverse: true,
                data: ranked.map((row) => texts.countryLabel(row.country)),
                animationDuration: 300,
                animationDurationUpdate: 300,
                max: 13,
            },
            series: [
                {
                    realtimeSort: true,
                    type: 'bar',
                    data: ranked.map((row) => ({
                        value: row.investmentBillionsUsd,
                        itemStyle: { color },
                    })),
                    label: {
                        show: true,
                        position: 'right',
                        valueAnimation: true,
                        formatter: '{c} B',
                    },
                    itemStyle: { color },
                },
            ],
        };
    };

    return buildBarRaceBase(years, maxInvestment, axisName, texts, buildFrame);
}
