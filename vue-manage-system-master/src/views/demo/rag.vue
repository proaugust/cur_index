<template>
    <div class="container rag-page">
        <div class="page-title-bar mgb20">
            <span class="page-title">{{ t('pages.rag.title') }}</span>
            <FeatureIntroIcon
                page-key="rag"
                section-key="page"
                :intros="intros"
                :title="t('pages.rag.title')"
                @saved="setIntro"
            />
        </div>

        <el-tabs v-model="activeTab" type="border-card" class="rag-tabs">
            <el-tab-pane :label="t('pages.rag.documentSection')" name="document" lazy>
                <LazyApiDebugPanel
                    endpoint-key="document"
                    intro-page-key="rag"
                    :intros="intros"
                    @intro-saved="setIntro"
                />
            </el-tab-pane>
            <el-tab-pane :label="t('pages.rag.corporaSection')" name="corpora" lazy>
                <CorporaBrowsePanel
                    intro-page-key="rag"
                    :intros="intros"
                    @intro-saved="setIntro"
                />
                <LazyApiDebugPanel
                    endpoint-key="corpora"
                    intro-page-key="rag"
                    :intros="intros"
                    @intro-saved="setIntro"
                />
            </el-tab-pane>
        </el-tabs>
    </div>
</template>

<script setup lang="ts" name="demo-rag">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import LazyApiDebugPanel from '@/components/lazy-api-debug-panel.vue';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import CorporaBrowsePanel from '@/views/demo/corpora-browse-panel.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('rag');
const activeTab = ref('document');
</script>

<style scoped>
.page-title-bar {
    display: inline-flex;
    align-items: center;
    padding: 4px 0;
}

.page-title {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
}

.mgb20 {
    margin-bottom: 16px;
}
</style>
