<template>
    <el-icon class="feature-intro-icon" :title="t('featureIntro.tooltip')" @click.stop="openDialog">
        <ChatDotRound />
    </el-icon>

    <el-dialog
        v-model="visible"
        :title="t('featureIntro.dialogTitle', { title: title || t('featureIntro.fallbackTitle') })"
        width="1040px"
        append-to-body
        destroy-on-close
        @closed="draft = ''"
    >
        <p class="feature-intro-hint">{{ t('featureIntro.hint') }}</p>
        <el-input
            v-model="draft"
            type="textarea"
            :rows="15"
            maxlength="2000"
            show-word-limit
            :placeholder="t('featureIntro.placeholder')"
        />
        <template #footer>
            <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">{{ t('common.save') }}</el-button>
        </template>
    </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ChatDotRound } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { upsertFeatureIntro } from '@/api';
import type { FeatureIntroMap } from '@/composables/useFeatureIntros';

const { t } = useI18n();

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
        ElMessage.success(t('featureIntro.saved'));
        visible.value = false;
    } catch {
        ElMessage.error(t('featureIntro.saveFailed'));
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
