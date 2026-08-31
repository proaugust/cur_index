<template>
    <el-card shadow="hover" class="demo-panel">
        <div class="panel-title">{{ title }}</div>
        <p class="panel-desc">{{ description }}</p>
        <el-form label-width="100px" class="param-form" @submit.prevent="onSubmit">
            <div @keyup.enter="onEnter">
                <slot name="fields" />
            </div>
            <el-form-item>
                <el-button type="primary" native-type="button" :loading="loading" @click="onSubmit">运行</el-button>
            </el-form-item>
        </el-form>
        <div v-if="answer" class="answer-box">
            <div class="answer-label">回答</div>
            <div class="answer-body">{{ answer }}</div>
        </div>
        <slot name="extra" />
    </el-card>
</template>

<script setup lang="ts" name="rag-demo-shell">
const props = defineProps<{ title: string; description: string; loading: boolean; answer?: string }>();
const emit = defineEmits<{ submit: [] }>();

const onSubmit = () => {
    if (props.loading) return;
    emit('submit');
};

const onEnter = (e: KeyboardEvent) => {
    if (e.isComposing || e.keyCode === 229) return;
    const tag = (e.target as HTMLElement).tagName;
    if (tag !== 'INPUT' && tag !== 'TEXTAREA') return;
    onSubmit();
};
</script>

<style scoped>
.demo-panel { margin-bottom: 16px; }
.panel-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.panel-desc { margin: 0 0 12px; color: #909399; font-size: 13px; }
.param-form { max-width: 640px; }
.answer-box { margin: 12px 0; padding: 12px 14px; background: #f5f7fa; border-radius: 6px; }
.answer-label { font-size: 13px; color: #606266; margin-bottom: 6px; }
.answer-body { white-space: pre-wrap; word-break: break-word; line-height: 1.6; font-size: 14px; }
</style>
