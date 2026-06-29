<template>
    <div class="agent-demo">
        <div v-if="hint" class="demo-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ hint }}</span>
        </div>

        <div v-if="examples?.length" class="example-row">
            <span class="example-label">{{ t('pages.agent.clickExample') }}</span>
            <el-tooltip
                v-for="item in examples"
                :key="item.label"
                :content="item.tip"
                placement="top"
            >
                <el-button
                    size="small"
                    :type="question === item.question ? 'primary' : 'default'"
                    :disabled="loading"
                    @click="runExample(item.question)"
                >
                    {{ item.label }}
                </el-button>
            </el-tooltip>
        </div>

        <div class="input-row">
            <el-input
                v-model="question"
                type="textarea"
                :rows="2"
                :placeholder="placeholder || t('pages.agent.placeholderDefault')"
                :disabled="loading"
            />
            <el-button type="primary" :loading="loading" @click="runCurrent">
                {{ t('pages.agent.runDemo') }}
            </el-button>
        </div>

        <div v-if="steps.length" class="steps-timeline">
            <div
                v-for="(step, i) in steps"
                :key="i"
                class="step-card"
                :class="step.status"
            >
                <div class="step-header">
                    <el-tag
                        :type="statusTagType(step.status)"
                        size="small"
                        effect="plain"
                    >
                        {{ statusLabel(step.status) }}
                    </el-tag>
                    <span class="step-agent">{{ step.agent }}</span>
                    <span class="step-role">{{ step.role }}</span>
                    <span v-if="step.meta" class="step-meta">{{ step.meta }}</span>
                </div>

                <div v-if="step.input && step.status !== 'pending'" class="step-block">
                    <div class="block-label">{{ t('pages.agent.input') }}</div>
                    <div class="block-content input-content">{{ truncate(step.input) }}</div>
                </div>

                <div v-if="step.output" class="step-block">
                    <div class="block-label">{{ t('pages.agent.output') }}</div>
                    <div class="block-content output-content">{{ step.output }}</div>
                </div>

                <div v-else-if="step.status === 'running'" class="step-loading">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    <span>{{ t('pages.agent.running') }}</span>
                </div>
            </div>
        </div>

        <el-empty
            v-else
            :description="emptyText || t('pages.agent.emptyDefault')"
            :image-size="80"
        />
    </div>
</template>

<script setup lang="ts">
import { watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { InfoFilled, Loading } from '@element-plus/icons-vue';
import { hasDemoCache, useCachedRef } from '@/composables/useFormCache';
import type { AgentExample, AgentStep } from './types';

const { t } = useI18n();

const props = withDefaults(
    defineProps<{
        loading: boolean;
        steps: AgentStep[];
        cacheKey: string;
        initialQuestion?: string;
        placeholder?: string;
        hint?: string;
        emptyText?: string;
        examples?: AgentExample[];
    }>(),
    {
        initialQuestion: '',
    },
);

const emit = defineEmits<{
    run: [question: string];
}>();

const question = useCachedRef(`agent:question:${props.cacheKey}`, props.initialQuestion);

watch(
    () => props.initialQuestion,
    (value) => {
        if (value && !hasDemoCache(`agent:question:${props.cacheKey}`)) {
            question.value = value;
        }
    },
);

const runCurrent = () => emit('run', question.value);

const runExample = (text: string) => {
    question.value = text;
    emit('run', text);
};

const statusTagType = (status: AgentStep['status']) => {
    const map = {
        pending: 'info',
        running: 'warning',
        done: 'success',
        error: 'danger',
    } as const;
    return map[status];
};

const statusLabel = (status: AgentStep['status']) => {
    const map = {
        pending: t('pages.agent.statusPending'),
        running: t('pages.agent.statusRunning'),
        done: t('pages.agent.statusDone'),
        error: t('pages.agent.statusError'),
    };
    return map[status];
};

const truncate = (text: string, max = 300) =>
    text.length > max ? `${text.slice(0, max)}...` : text;
</script>

<style scoped>
.agent-demo {
    margin-top: 4px;
}

.demo-hint {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    margin-bottom: 12px;
    font-size: 13px;
    line-height: 1.6;
    color: #606266;
    background: #f4f4f5;
    border-radius: 6px;
}

.demo-hint .el-icon {
    margin-top: 3px;
    color: #909399;
    flex-shrink: 0;
}

.example-row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
}

.example-label {
    font-size: 13px;
    color: #909399;
}

.input-row {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: 20px;
}

.input-row .el-input {
    flex: 1;
}

.steps-timeline {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.step-card {
    padding: 14px 16px;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    background: #fafafa;
    transition: border-color 0.2s;
}

.step-card.running {
    border-color: #e6a23c;
    background: #fdf6ec;
}

.step-card.done {
    border-color: #e1f3d8;
    background: #f0f9eb;
}

.step-card.error {
    border-color: #fde2e2;
    background: #fef0f0;
}

.step-header {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 10px;
}

.step-agent {
    font-weight: 600;
    font-size: 14px;
    color: #303133;
}

.step-role {
    font-size: 13px;
    color: #909399;
}

.step-meta {
    font-size: 12px;
    color: #e6a23c;
    margin-left: auto;
}

.step-block {
    margin-top: 8px;
}

.block-label {
    font-size: 12px;
    color: #909399;
    margin-bottom: 4px;
}

.block-content {
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
    padding: 8px 10px;
    border-radius: 4px;
}

.input-content {
    background: #f5f7fa;
    color: #606266;
    max-height: 120px;
    overflow-y: auto;
}

.output-content {
    background: #fff;
    color: #303133;
    border: 1px solid #ebeef5;
}

.step-loading {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: #e6a23c;
    margin-top: 8px;
}
</style>
