import csvRaw from './global_ai_trends_2015_2026.csv?raw';

export interface AiTrendRow {
    year: number;
    country: string;
    aiIndexScore: number;
    investmentBillionsUsd: number;
    publishedPapersThousands: number;
    aiTalentPoolThousands: number;
    primaryFocusArea: string;
}

export const COUNTRY_LABELS: Record<string, string> = {
    'United States': '美国',
    China: '中国',
    'United Kingdom': '英国',
    Germany: '德国',
    France: '法国',
    Japan: '日本',
    'South Korea': '韩国',
    Singapore: '新加坡',
    India: '印度',
    Canada: '加拿大',
    Israel: '以色列',
    Australia: '澳大利亚',
    Brazil: '巴西',
    'United Arab Emirates': '阿联酋',
};

/** CSV Country_Region → ECharts world.json properties.name */
export const GEO_NAME_MAP: Record<string, string> = {
    'United States': 'United States',
    China: 'China',
    'United Kingdom': 'United Kingdom',
    Germany: 'Germany',
    France: 'France',
    Japan: 'Japan',
    'South Korea': 'Korea',
    Singapore: 'Singapore',
    India: 'India',
    Canada: 'Canada',
    Israel: 'Israel',
    Australia: 'Australia',
    Brazil: 'Brazil',
    'United Arab Emirates': 'United Arab Emirates',
};

const COUNTRY_COLORS = [
    '#2d8cf0',
    '#f25e43',
    '#64d572',
    '#e9a745',
    '#9b59b6',
    '#00bcd4',
    '#1abc9c',
    '#e74c3c',
    '#3498db',
    '#f39c12',
    '#8e44ad',
    '#16a085',
    '#d35400',
    '#7f8c8d',
];

const LATEST_YEAR = 2026;

export interface DashboardChartTexts {
    countryLabel: (country: string) => string;
    aiIndex: string;
    investmentBillion: string;
    investmentAxis: string;
    yearSuffix: string;
    othersRegion: string;
    mapHigh: string;
    mapLow: string;
    noData: string;
    formatTooltipIndex: (score: number) => string;
    formatTooltipInvestment: (v: number) => string;
    formatTooltipPapers: (v: number) => string;
}

const DEFAULT_CHART_TEXTS: DashboardChartTexts = {
    countryLabel: (country) => COUNTRY_LABELS[country] ?? country,
    aiIndex: 'AI 指数',
    investmentBillion: '十亿美元',
    investmentAxis: '投资 (十亿美元)',
    yearSuffix: ' 年',
    othersRegion: '其他地区',
    mapHigh: '高',
    mapLow: '低',
    noData: '暂无数据',
    formatTooltipIndex: (score) => `AI 指数：${score}`,
    formatTooltipInvestment: (v) => `投资：${v} 十亿美元`,
    formatTooltipPapers: (v) => `论文：${v} 千篇`,
};

function parseCsv(raw: string): AiTrendRow[] {
    const lines = raw.trim().split(/\r?\n/);
    return lines.slice(1).map((line) => {
        const parts = line.split(',');
        return {
            year: Number(parts[0]),
            country: parts[1],
            aiIndexScore: Number(parts[2]),
            investmentBillionsUsd: Number(parts[3]),
            publishedPapersThousands: Number(parts[4]),
            aiTalentPoolThousands: Number(parts[5]),
            primaryFocusArea: parts.slice(6).join(','),
        };
    });
}

export const AI_TRENDS_DATA: AiTrendRow[] = parseCsv(csvRaw);

function getYears(data: AiTrendRow[] = AI_TRENDS_DATA): number[] {
    return [...new Set(data.map((row) => row.year))].sort((a, b) => a - b);
}

function getCountries(data: AiTrendRow[] = AI_TRENDS_DATA): string[] {
    const latest = data.filter((row) => row.year === LATEST_YEAR)
        .sort((a, b) => b.aiIndexScore - a.aiIndexScore)
        .map((row) => row.country);
    return latest;
}

function rowsByYear(data: AiTrendRow[], year: number): AiTrendRow[] {
    return data.filter((row) => row.year === year);
}

function countryColor(data: AiTrendRow[], country: string): string {
    const countries = getCountries(data);
    const index = countries.indexOf(country);
    return COUNTRY_COLORS[index >= 0 ? index : 0] ?? '#2d8cf0';
}

export function buildIndexTrendOption(customData?: AiTrendRow[], texts: DashboardChartTexts = DEFAULT_CHART_TEXTS) {
    const data = customData || AI_TRENDS_DATA;
    const years = getYears(data).map(String);
    const countries = getCountries(data);

    return {
        tooltip: {
            trigger: 'axis',
        },
        legend: {
            type: 'scroll',
            top: 0,
            data: countries.map((country) => texts.countryLabel(country)),
        },
        grid: {
            top: '14%',
            left: '2%',
            right: '3%',
            bottom: '2%',
            containLabel: true,
        },
        color: COUNTRY_COLORS,
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: years,
        },
        yAxis: {
            type: 'value',
            name: texts.aiIndex,
            min: 0,
            max: 105,
        },
        series: countries.map((country) => ({
            name: texts.countryLabel(country),
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 5,
            showSymbol: false,
            emphasis: { focus: 'series' },
            data: years.map((year) => {
                const row = data.find((item) => item.year === Number(year) && item.country === country);
                return row?.aiIndexScore ?? null;
            }),
        })),
    };
}

export function buildInvestmentBarRaceOption(customData?: AiTrendRow[], texts: DashboardChartTexts = DEFAULT_CHART_TEXTS) {
    const data = customData || AI_TRENDS_DATA;
    const years = getYears(data);
    const maxInvestment = Math.ceil(Math.max(...data.map((row) => row.investmentBillionsUsd)) * 1.1);

    const buildFrame = (year: number) => {
        const ranked = [...rowsByYear(data, year)].sort((a, b) => a.investmentBillionsUsd - b.investmentBillionsUsd);

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
                        itemStyle: { color: countryColor(data, row.country) },
                    })),
                    label: {
                        show: true,
                        position: 'right',
                        valueAnimation: true,
                        formatter: '{c} B',
                    },
                },
            ],
        };
    };

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
                name: texts.investmentAxis,
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

export function buildInvestmentPieOption(customData?: AiTrendRow[], texts: DashboardChartTexts = DEFAULT_CHART_TEXTS) {
    const data = customData || AI_TRENDS_DATA;
    const latest = [...rowsByYear(data, LATEST_YEAR)].sort((a, b) => b.investmentBillionsUsd - a.investmentBillionsUsd).slice(0, 6);
    const othersInvestment = rowsByYear(data, LATEST_YEAR)
        .filter((row) => !latest.some((item) => item.country === row.country))
        .reduce((sum, row) => sum + row.investmentBillionsUsd, 0);

    const pieData = latest.map((row) => ({
        name: texts.countryLabel(row.country),
        value: Math.round(row.investmentBillionsUsd * 100) / 100,
    }));

    if (othersInvestment > 0) {
        pieData.push({ name: texts.othersRegion, value: Math.round(othersInvestment * 100) / 100 });
    }

    return {
        tooltip: {
            trigger: 'item',
            formatter: `{b}: {c} ${texts.investmentBillion} ({d}%)`,
        },
        legend: {
            type: 'scroll',
            bottom: '1%',
            left: 'center',
        },
        color: COUNTRY_COLORS,
        series: [
            {
                type: 'pie',
                radius: ['40%', '70%'],
                itemStyle: {
                    borderRadius: 8,
                    borderColor: '#fff',
                    borderWidth: 2,
                },
                label: {
                    show: true,
                    formatter: '{b}\n{d}%',
                },
                data: pieData,
            },
        ],
    };
}

export function buildSummaryCards(customData?: AiTrendRow[]) {
    const data = customData || AI_TRENDS_DATA;
    const latest = rowsByYear(data, LATEST_YEAR);
    const totalInvestment = latest.reduce((sum, row) => sum + row.investmentBillionsUsd, 0);
    const totalPapers = latest.reduce((sum, row) => sum + row.publishedPapersThousands, 0);
    const avgScore = latest.reduce((sum, row) => sum + row.aiIndexScore, 0) / latest.length;
    const usRow = latest.find((row) => row.country === 'United States');

    return {
        usIndex: usRow?.aiIndexScore ?? 0,
        totalInvestment: Math.round(totalInvestment * 10) / 10,
        totalPapers: Math.round(totalPapers * 10) / 10,
        avgScore: Math.round(avgScore * 10) / 10,
        countryCount: latest.length,
    };
}

export function buildWorldMapOption(customData?: AiTrendRow[], year: number = LATEST_YEAR, texts: DashboardChartTexts = DEFAULT_CHART_TEXTS) {
    const data = customData || AI_TRENDS_DATA;
    const rows = rowsByYear(data, year);

    type MapDataItem = {
        name: string;
        value: number;
        label: string;
        investment: number;
        papers: number;
    };

    const mapData: MapDataItem[] = rows.map((row) => ({
        name: GEO_NAME_MAP[row.country] ?? row.country,
        value: row.aiIndexScore,
        label: texts.countryLabel(row.country),
        investment: row.investmentBillionsUsd,
        papers: row.publishedPapersThousands,
    }));

    const dataByGeoName = new Map(mapData.map((item) => [item.name, item]));

    return {
        tooltip: {
            trigger: 'item',
            formatter: (raw: unknown) => {
                const params = (Array.isArray(raw) ? raw[0] : raw) as {
                    name?: string;
                    data?: MapDataItem | number;
                    value?: number | null;
                    dataIndex?: number;
                };

                let item: MapDataItem | undefined;
                if (typeof params.dataIndex === 'number' && params.dataIndex >= 0) {
                    item = mapData[params.dataIndex];
                } else if (params.data && typeof params.data === 'object') {
                    item = params.data as MapDataItem;
                } else if (params.name) {
                    item = dataByGeoName.get(params.name);
                }

                const score = item?.value ?? params.value;
                if (!item || score == null || Number.isNaN(Number(score))) {
                    return `${params.name ?? ''}<br/>${texts.noData}`;
                }

                return [
                    item.label,
                    texts.formatTooltipIndex(Number(score)),
                    texts.formatTooltipInvestment(item.investment),
                    texts.formatTooltipPapers(item.papers),
                ].join('<br/>');
            },
        },
        visualMap: {
            min: 0,
            max: 100,
            left: 16,
            bottom: 24,
            text: [texts.mapHigh, texts.mapLow],
            calculable: true,
            seriesIndex: 0,
            inRange: {
                color: ['#e8f4fc', '#5cadff', '#2d8cf0', '#f25e43'],
            },
        },
        geo: {
            map: 'world',
            roam: true,
            scaleLimit: { min: 1, max: 4 },
            emphasis: {
                label: { show: false },
                itemStyle: { areaColor: '#ffd666' },
            },
            itemStyle: {
                areaColor: '#f3f4f6',
                borderColor: '#fff',
                borderWidth: 0.6,
            },
        },
        series: [
            {
                name: texts.aiIndex,
                type: 'map',
                geoIndex: 0,
                coordinateSystem: 'geo',
                map: 'world',
                data: mapData,
                emphasis: {
                    label: {
                        show: true,
                        formatter: (raw: { name?: string; data?: MapDataItem }) => {
                            const data = raw.data;
                            if (data && typeof data === 'object' && data.label) {
                                return data.label;
                            }
                            return raw.name ?? '';
                        },
                    },
                },
            },
        ],
    };
}

export function buildRegionRanks(customData?: AiTrendRow[], texts: DashboardChartTexts = DEFAULT_CHART_TEXTS) {
    const data = customData || AI_TRENDS_DATA;
    const latest = [...rowsByYear(data, LATEST_YEAR)].sort((a, b) => b.aiIndexScore - a.aiIndexScore).slice(0, 5);
    const maxScore = latest[0]?.aiIndexScore ?? 100;

    return latest.map((row, index) => ({
        title: texts.countryLabel(row.country),
        value: row.aiIndexScore,
        percent: Math.round((row.aiIndexScore / maxScore) * 100),
        color: COUNTRY_COLORS[index] ?? '#2d8cf0',
    }));
}

export const aiMilestones = [
    {
        content: '2015 起点',
        description: '美国 AI 指数 47.9，14 国/地区纳入统计',
        timestamp: '2015',
        color: '#787878',
    },
    {
        content: '2018 中国加速',
        description: '中国指数 40.8，发表论文 27.8 千篇',
        timestamp: '2018',
        color: '#f25e43',
    },
    {
        content: '2023 生成式 AI 爆发',
        description: '美国指数 83.6，投资 22.44 十亿美元',
        timestamp: '2023',
        color: '#2d8cf0',
    },
    {
        content: '2025 人才规模扩大',
        description: '印度 AI 人才池 294.6 千人，全球领先',
        timestamp: '2025',
        color: '#e9a745',
    },
    {
        content: '2026 美国满分',
        description: '美国 AI 指数 100.0，全球投资合计逾 70 十亿美元',
        timestamp: '2026',
        color: '#64d572',
    },
];
