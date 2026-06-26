<template>
    <div class="container smart-route-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">智能路由</span>
                    <span class="page-subtitle">根据一句话判断应调用哪条后端接口（仅路由展示，不执行业务）</span>
                </div>
            </template>

            <div class="quick-section">
                <div class="section-label">快捷提问</div>
                <div class="quick-buttons">
                    <el-button
                        v-for="item in quickQuestions"
                        :key="item"
                        :disabled="loading"
                        @click="handleQuick(item)"
                    >
                        {{ item }}
                    </el-button>
                </div>
            </div>

            <div class="input-section">
                <div class="section-label">自定义问题</div>
                <el-input
                    v-model="question"
                    type="textarea"
                    :rows="3"
                    placeholder="输入一句话，例如：明天会下雨吗？"
                    :disabled="loading"
                    @keydown.ctrl.enter="handleDispatch"
                />
                <div class="action-bar">
                    <el-button type="primary" :loading="loading" :disabled="!question.trim()" @click="handleDispatch">
                        路由判断
                    </el-button>
                    <el-button :disabled="loading || !question" @click="handleClear">清空</el-button>
                </div>
            </div>

            <el-divider />

            <div class="output-section">
                <div class="section-label">路由结果</div>
                <div v-if="routeMessage" class="result-box">
                    <el-tag v-if="routeIntent" :type="intentTagType" size="small" class="intent-tag">
                        {{ intentLabel }}
                    </el-tag>
                    <span class="route-message">{{ routeMessage }}</span>
                </div>
                <el-empty v-else description="路由结论将显示在这里" :image-size="80" />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-smart-route">
import { computed, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { smartRouteDispatch } from '@/api';

const quickQuestions = [
    '今天天气怎么样？',
    '查询员工张三的信息',
    '帮我发邮件',
];

const question = ref('');
const routeMessage = ref('');
const routeIntent = ref('');
const loading = ref(false);

const intentMap: Record<string, { label: string; type: '' | 'success' | 'warning' | 'info' | 'danger' }> = {
    weather: { label: '天气', type: 'success' },
    employee: { label: '员工', type: 'warning' },
    email: { label: '邮件', type: 'info' },
    unknown: { label: '兜底', type: 'danger' },
};

const intentLabel = computed(() => intentMap[routeIntent.value]?.label ?? routeIntent.value);
const intentTagType = computed(() => intentMap[routeIntent.value]?.type ?? 'info');

const handleDispatch = async () => {
    const q = question.value.trim();
    if (!q) return;

    loading.value = true;
    routeMessage.value = '';
    routeIntent.value = '';
    try {
        const res = await smartRouteDispatch({ question: q });
        routeMessage.value = res.data.message;
        routeIntent.value = res.data.intent;
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(typeof msg === 'string' ? msg : '路由判断失败，请稍后重试');
    } finally {
        loading.value = false;
    }
};

const handleQuick = (text: string) => {
    question.value = text;
    handleDispatch();
};

const handleClear = () => {
    question.value = '';
    routeMessage.value = '';
    routeIntent.value = '';
};
</script>

<style scoped>
.smart-route-page .page-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.smart-route-page .page-title {
    font-size: 16px;
    font-weight: 600;
}

.smart-route-page .page-subtitle {
    font-size: 13px;
    color: var(--el-text-color-secondary);
}

.section-label {
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 500;
}

.quick-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.input-section {
    margin-top: 20px;
}

.action-bar {
    margin-top: 12px;
    display: flex;
    gap: 8px;
}

.result-box {
    min-height: 80px;
    padding: 16px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 4px;
    background: var(--el-fill-color-blank);
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 16px;
}

.route-message {
    font-weight: 500;
}
</style>
