import type { ComposeOption } from 'echarts/core';
import type { MapSeriesOption, VisualMapComponentOption } from 'echarts';

/** 关东及周边都县（与 kanto-geo.json 一致）；仅有数据的会渲染 */
export const NEARBY_PREFECTURES = [
    '东京都',
    '神奈川县',
    '千叶县',
    '埼玉县',
    '茨城县',
    '栃木县',
    '群马县',
    '山梨县',
    '静冈县',
] as const;

export type NearbyPrefecture = (typeof NEARBY_PREFECTURES)[number];

const NEARBY_SET = new Set<string>(NEARBY_PREFECTURES);

export interface RegionMetricRow {
    snapshot_date: string;
    region_l1: string;
    region_l2: string;
    total_customers: number;
    high_risk_ratio: number;
    risk_ratio_mom: number;
}

export interface L1Aggregate {
    region_l1: string;
    total_customers: number;
    high_risk_ratio: number;
    risk_ratio_mom: number;
    cities: RegionMetricRow[];
}

export interface MapTexts {
    highRisk: string;
    lowRisk: string;
    customers: string;
    mom: string;
    noData: string;
}

export interface GeoFeatureCollection {
    type: 'FeatureCollection';
    features: Array<{
        type: string;
        properties: { name: string; cp?: number[] };
        geometry: unknown;
    }>;
}

export type RegionMapOption = ComposeOption<MapSeriesOption | VisualMapComponentOption>;

export function pickLatestRows(rows: RegionMetricRow[]): RegionMetricRow[] {
    if (!rows.length) return [];
    const latest = rows[0].snapshot_date;
    return rows.filter((row) => row.snapshot_date === latest);
}

/** 仅聚合周边目录内、且有客户数据的一级区域 */
export function aggregateByL1(rows: RegionMetricRow[]): L1Aggregate[] {
    const latestRows = pickLatestRows(rows);
    const grouped = new Map<string, RegionMetricRow[]>();
    for (const row of latestRows) {
        if (!NEARBY_SET.has(row.region_l1)) continue;
        const bucket = grouped.get(row.region_l1) ?? [];
        bucket.push(row);
        grouped.set(row.region_l1, bucket);
    }

    const aggregates: L1Aggregate[] = [];
    for (const prefecture of NEARBY_PREFECTURES) {
        const cities = grouped.get(prefecture) ?? [];
        if (!cities.length) continue;
        const totalCustomers = cities.reduce((sum, item) => sum + Number(item.total_customers), 0);
        if (totalCustomers <= 0) continue;
        const weightedRisk =
            cities.reduce((sum, item) => sum + Number(item.high_risk_ratio) * Number(item.total_customers), 0) /
            totalCustomers;
        const weightedMom =
            cities.reduce((sum, item) => sum + Number(item.risk_ratio_mom) * Number(item.total_customers), 0) /
            totalCustomers;
        aggregates.push({
            region_l1: prefecture,
            total_customers: totalCustomers,
            high_risk_ratio: weightedRisk,
            risk_ratio_mom: weightedMom,
            cities: cities.sort((a, b) => Number(b.high_risk_ratio) - Number(a.high_risk_ratio)),
        });
    }
    return aggregates;
}

/** 按有数据的都县裁剪 GeoJSON，无数据区域不进入地图 */
export function filterGeoByRegions(geo: GeoFeatureCollection, regionNames: string[]): GeoFeatureCollection {
    const allow = new Set(regionNames);
    return {
        type: 'FeatureCollection',
        features: geo.features.filter((feature) => allow.has(feature.properties?.name)),
    };
}

export function buildSummary(aggregates: L1Aggregate[], snapshotDate: string | null) {
    const totalCustomers = aggregates.reduce((sum, item) => sum + item.total_customers, 0);
    const avgRisk =
        totalCustomers > 0
            ? aggregates.reduce((sum, item) => sum + item.high_risk_ratio * item.total_customers, 0) / totalCustomers
            : 0;
    return {
        snapshotDate,
        totalCustomers,
        avgHighRisk: avgRisk,
        regionCount: aggregates.length,
        cityCount: aggregates.reduce((sum, item) => sum + item.cities.length, 0),
    };
}

export function buildRegionMapOption(
    aggregates: L1Aggregate[],
    texts: MapTexts,
    selected?: string | null,
): RegionMapOption {
    const byName = new Map(aggregates.map((item) => [item.region_l1, item]));
    // 周边都县全部进地图：有数据着色，无数据走默认灰底
    const mapData = NEARBY_PREFECTURES.map((name) => {
        const item = byName.get(name);
        if (!item || item.total_customers <= 0) {
            return {
                name,
                value: null as number | null,
                customers: 0,
                mom: 0,
                selected: name === selected,
                itemStyle: { areaColor: '#e2e8f0' },
            };
        }
        return {
            name,
            value: Number((item.high_risk_ratio * 100).toFixed(2)),
            customers: item.total_customers,
            mom: item.risk_ratio_mom,
            selected: name === selected,
        };
    });
    const valued = mapData.filter((item) => item.value != null).map((item) => Number(item.value));
    const maxValue = Math.max(5, ...valued, 0);

    return {
        tooltip: {
            trigger: 'item',
            formatter: (params: { name?: string; data?: { customers?: number; value?: number | null; mom?: number } }) => {
                const data = params.data;
                if (!data || !data.customers) return `${params.name ?? ''}<br/>${texts.noData}`;
                const mom = Number(data.mom ?? 0) * 100;
                const momText = `${mom >= 0 ? '+' : ''}${mom.toFixed(2)}%`;
                return [
                    `<strong>${params.name ?? ''}</strong>`,
                    `${texts.customers}：${data.customers}`,
                    `${texts.highRisk}：${Number(data.value ?? 0).toFixed(2)}%`,
                    `${texts.mom}：${momText}`,
                ].join('<br/>');
            },
        },
        visualMap: {
            min: 0,
            max: maxValue,
            left: 16,
            bottom: 16,
            calculable: false,
            text: [texts.highRisk, texts.lowRisk],
            inRange: {
                color: ['#dbeafe', '#60a5fa', '#f59e0b', '#ef4444'],
            },
            textStyle: { color: '#475569' },
            show: valued.length > 0,
        },
        series: [
            {
                name: 'region-risk',
                type: 'map',
                map: 'insight-kanto',
                roam: true,
                zoom: 1.05,
                layoutCenter: ['50%', '50%'],
                layoutSize: '96%',
                selectedMode: 'single',
                nameProperty: 'name',
                label: {
                    show: true,
                    color: '#0f172a',
                    fontSize: 11,
                },
                emphasis: {
                    label: { show: true, fontWeight: 'bold' },
                    itemStyle: { areaColor: '#fbbf24', borderColor: '#0f172a', borderWidth: 1.2 },
                },
                select: {
                    itemStyle: { areaColor: '#f97316', borderColor: '#7c2d12', borderWidth: 1.5 },
                    label: { color: '#fff', fontWeight: 'bold' },
                },
                itemStyle: {
                    borderColor: '#64748b',
                    borderWidth: 1.1,
                    areaColor: '#e2e8f0',
                },
                data: mapData,
            },
        ],
    };
}
