<template>
    <el-icon class="feature-intro-icon" title="功能介绍" @click.stop="openDialog">
        <ChatDotRound />
    </el-icon>

    <el-dialog
        v-model="visible"
        :title="`${title || '功能介绍'} — 说明`"
        width="1040px"
        append-to-body
        destroy-on-close
        @closed="draft = ''"
    >
        <p class="feature-intro-hint">在此填写该 Tab / 功能块的说明，保存后写入数据库，所有用户可见。</p>
        <el-input
            v-model="draft"
            type="textarea"
            :rows="15"
            maxlength="2000"
            show-word-limit
            placeholder="例如：本页用于文档向量检索与大模型润色演示……"
        />
        <template #footer>
            <el-button @click="visible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </template>
    </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ChatDotRound } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { upsertFeatureIntro } from '@/api';
import type { FeatureIntroMap } from '@/composables/useFeatureIntros';

const props = defineProps<{
    pageKey: string;
    sectionKey: string;
    intros: FeatureIntroMap;
    title?: string;
}>();

const emit = defineEmits<{
    saved: [sectionKey: string, content: string];
}>();

const visible = ref(false);
const draft = ref('');
const saving = ref(false);

const openDialog = () => {
    draft.value = props.intros[props.sectionKey] ?? '';
    visible.value = true;
};

const handleSave = async () => {
    saving.value = true;
    try {
        const content = draft.value.trim();
        await upsertFeatureIntro(props.pageKey, props.sectionKey, {
            title: props.title ?? '',
            content,
        });
        emit('saved', props.sectionKey, content);
        ElMessage.success('功能说明已保存');
        visible.value = false;
    } catch {
        ElMessage.error('保存失败，请检查后端是否已启动');
    } finally {
        saving.value = false;
    }
};
</script>

<style scoped>
.feature-intro-icon {
    margin-left: 6px;
    font-size: 17px;
    color: #409eff;
    cursor: pointer;
    vertical-align: middle;
}

.feature-intro-icon:hover {
    color: #66b1ff;
}

.feature-intro-hint {
    margin: 0 0 12px;
    font-size: 13px;
    color: #909399;
    line-height: 1.5;
}
</style>
