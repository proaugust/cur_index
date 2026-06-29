<template>
    <div class="call-graph-panel">
        <v-chart v-if="VChart" class="graph-chart" :option="chartOption" autoresize />
        <div v-else class="graph-loading">{{ t('pages.cobolMigrate.graphLoading') }}</div>
        <el-collapse class="edge-collapse">
            <el-collapse-item :title="t('pages.cobolMigrate.edgeTableTitle')" name="edges">
                <el-table :data="edges" stripe size="small" max-height="220">
                    <el-table-column prop="source" :label="t('pages.cobolMigrate.colSource')" width="140" />
                    <el-table-column prop="target" :label="t('pages.cobolMigrate.colTarget')" width="140" />
                    <el-table-column prop="relation" :label="t('pages.cobolMigrate.colRelation')" width="100" />
                </el-table>
            </el-collapse-item>
        </el-collapse>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, shallowRef, type Component } from 'vue';
import { useI18n } from 'vue-i18n';

interface GraphNode {
    id: string;
    name: string;
    category: string;
    symbol_size?: number;
}

interface GraphEdge {
    source: string;
    target: string;
    relation: string;
}

const props = defineProps<{
    nodes: GraphNode[];
    edges: GraphEdge[];
}>();

const { t } = useI18n();
const VChart = shallowRef<Component | null>(null);

const categoryMap = computed(() => ({
    program: t('pages.cobolMigrate.graphCategoryProgram'),
    copybook: t('pages.cobolMigrate.graphCategoryCopybook'),
}));

onMounted(async () => {
    const [core, charts, components, renderers, vueEcharts] = await Promise.all([
        import('echarts/core'),
        import('echarts/charts'),
        import('echarts/components'),
        import('echarts/renderers'),
        import('vue-echarts'),
    ]);
    core.use([
        renderers.CanvasRenderer,
        charts.GraphChart,
        components.TooltipComponent,
        components.LegendComponent,
    ]);
    VChart.value = vueEcharts.default;
});

const chartOption = computed(() => {
    const categories = [
        { name: categoryMap.value.program },
        { name: categoryMap.value.copybook },
    ];
    const categoryIndex = (cat: string) => (cat === 'copybook' ? 1 : 0);
    const data = props.nodes.map((node) => ({
        id: node.id,
        name: node.name,
        category: categoryIndex(node.category),
        symbolSize: node.symbol_size ?? 40,
        draggable: true,
    }));
    const links = props.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        value: edge.relation,
        lineStyle: {
            type: edge.relation === 'COPY' ? 'dashed' : 'solid',
            color: edge.relation === 'COPY' ? '#e6a23c' : '#409eff',
        },
    }));

    return {
        tooltip: {
            formatter: (params: { dataType?: string; data?: { name?: string; value?: string }; name?: string }) => {
                if (params.dataType === 'edge') {
                    return `${params.data?.value ?? ''}`;
                }
                return params.data?.name ?? params.name ?? '';
            },
        },
        legend: [{ data: categories.map((c) => c.name), bottom: 0 }],
        series: [
            {
                type: 'graph',
                layout: 'force',
                roam: true,
                categories,
                data,
                links,
                label: { show: true, fontSize: 11 },
                force: { repulsion: 280, edgeLength: [80, 160], gravity: 0.08 },
                emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
            },
        ],
    };
});
</script>

<style scoped>
.graph-chart {
    width: 100%;
    height: 380px;
}

.graph-loading {
    height: 380px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
    font-size: 13px;
    background: #fafafa;
    border: 1px dashed #dcdfe6;
    border-radius: 6px;
}

.edge-collapse {
    margin-top: 12px;
}
</style>
