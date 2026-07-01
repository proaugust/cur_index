<template>
    <div class="container ai-news-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.aiNews.title') }}</span>
                </div>
            </template>

            <p class="page-intro">{{ t('pages.aiNews.intro') }}</p>

            <div class="add-bar">
                <el-input
                    v-model="urlInput"
                    :placeholder="t('pages.aiNews.addPlaceholder')"
                    clearable
                    @keyup.enter="onAddUrl"
                />
                <el-button type="primary" :disabled="!urlInput.trim()" @click="onAddUrl">
                    {{ t('pages.aiNews.add') }}
                </el-button>
            </div>

            <el-row :gutter="20" class="columns-row">
                <el-col :xs="24" :md="8">
                    <div class="link-section panel-box">
                        <div class="section-label">{{ t('pages.aiNews.sectionInternational') }}</div>
                        <div class="link-list">
                            <LinkCard
                                v-for="item in internationalLinks"
                                :key="item.key"
                                :item="item"
                                :name="linkName(item)"
                                :desc="linkDesc(item)"
                                :icon-failed="!!iconFailed[item.key]"
                                :favorited="isFavoriteItem(item)"
                                @open="openLink"
                                @icon-error="markIconFailed"
                                @delete="onDeleteLink"
                                @favorite="onToggleFavorite"
                            />
                            <div v-if="!internationalLinks.length" class="empty-hint">
                                {{ t('pages.aiNews.emptySection') }}
                            </div>
                        </div>
                    </div>
                </el-col>
                <el-col :xs="24" :md="8">
                    <div class="link-section panel-box">
                        <div class="section-label">{{ t('pages.aiNews.sectionDomestic') }}</div>
                        <div class="link-list">
                            <LinkCard
                                v-for="item in domesticLinks"
                                :key="item.key"
                                :item="item"
                                :name="linkName(item)"
                                :desc="linkDesc(item)"
                                :icon-failed="!!iconFailed[item.key]"
                                :favorited="isFavoriteItem(item)"
                                @open="openLink"
                                @icon-error="markIconFailed"
                                @delete="onDeleteLink"
                                @favorite="onToggleFavorite"
                            />
                            <div v-if="!domesticLinks.length" class="empty-hint">
                                {{ t('pages.aiNews.emptySection') }}
                            </div>
                        </div>
                    </div>
                </el-col>
                <el-col :xs="24" :md="8">
                    <div class="favorites-panel panel-box">
                        <div class="section-label">
                            <el-icon class="fav-icon"><Star /></el-icon>
                            {{ t('pages.aiNews.favorites') }}
                        </div>
                        <p class="fav-hint">{{ t('pages.aiNews.favoritesHint') }}</p>
                        <div class="link-list link-list--grow">
                            <div
                                v-for="item in favoriteLinks"
                                :key="item.key"
                                class="link-item link-item--fav"
                                role="link"
                                tabindex="0"
                                @click="openLink(item.url)"
                                @keydown.enter="openLink(item.url)"
                                @keydown.space.prevent="openLink(item.url)"
                            >
                                <div
                                    v-if="iconFailed[item.key]"
                                    class="site-icon site-icon--letter"
                                    :style="{ background: item.color, color: letterColor(item.color) }"
                                >
                                    {{ item.letter }}
                                </div>
                                <img
                                    v-else
                                    class="site-icon"
                                    :src="item.icon"
                                    :alt="favoriteName(item)"
                                    loading="lazy"
                                    @error="markIconFailed(item.key)"
                                />
                                <div class="link-info">
                                    <div class="link-name">{{ favoriteName(item) }}</div>
                                    <div class="link-url">{{ item.url }}</div>
                                </div>
                                <el-button
                                    class="delete-btn"
                                    type="danger"
                                    link
                                    :title="t('pages.aiNews.removeFavorite')"
                                    @click.stop="onRemoveFavorite(item)"
                                >
                                    <el-icon><Close /></el-icon>
                                </el-button>
                            </div>
                            <div v-if="!favoriteLinks.length" class="fav-empty fav-empty--grow">
                                {{ t('pages.aiNews.favoritesEmpty') }}
                            </div>
                        </div>
                    </div>
                </el-col>
            </el-row>

            <div v-if="customLinks.length" class="link-section custom-section">
                <div class="section-label">{{ t('pages.aiNews.sectionCustom') }}</div>
                <div class="link-list">
                    <LinkCard
                        v-for="item in customLinks"
                        :key="item.key"
                        :item="item"
                        :name="item.type === 'custom' ? customTitle(item.id) : linkName(item)"
                        :desc="item.type === 'custom' ? item.url : linkDesc(item)"
                        :icon-failed="!!iconFailed[item.key]"
                        :favorited="isFavoriteItem(item)"
                        @open="openLink"
                        @icon-error="markIconFailed"
                        @delete="onDeleteLink"
                        @favorite="onToggleFavorite"
                    />
                </div>
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-ai-news">
import { computed, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { Close, Star } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { domesticLinkDefs, internationalLinkDefs } from './ai-news-links-data';
import {
    createCustomLinkFromUrl,
    type ResolvedLink,
    useAiNewsPrefs,
} from './ai-news-links-store';
import LinkCard from './ai-news-link-card.vue';

const { t } = useI18n();
const {
    prefs,
    filterPresets,
    resolvePreset,
    resolveCustom,
    hidePreset,
    removeCustom,
    addCustom,
    addFavorite,
    removeFavorite,
    isFavorite,
} = useAiNewsPrefs();

const urlInput = ref('');
const iconFailed = reactive<Record<string, boolean>>({});

const internationalLinks = computed(() =>
    filterPresets(internationalLinkDefs).map(resolvePreset),
);
const domesticLinks = computed(() => filterPresets(domesticLinkDefs).map(resolvePreset));
const customLinks = computed(() => prefs.value.customLinks.map(resolveCustom));

const presetMap = computed(() => {
    const map = new Map<string, ResolvedLink>();
    for (const d of [...internationalLinkDefs, ...domesticLinkDefs]) {
        map.set(d.id, resolvePreset(d));
    }
    return map;
});

const favoriteLinks = computed(() => {
    const result: ResolvedLink[] = [];
    for (const ref of prefs.value.favorites) {
        if (ref.type === 'preset') {
            const link = presetMap.value.get(ref.id);
            if (link && !prefs.value.hiddenPresetIds.includes(ref.id)) {
                result.push(link);
            }
        } else {
            const custom = prefs.value.customLinks.find((c) => c.id === ref.id);
            if (custom) result.push(resolveCustom(custom));
        }
    }
    return result;
});

const customTitle = (id: string) => prefs.value.customLinks.find((c) => c.id === id)?.title ?? '';

const linkName = (item: ResolvedLink) => {
    if (item.type === 'custom') return customTitle(item.id);
    return t(`pages.aiNews.links.${item.presetId}.name`);
};

const linkDesc = (item: ResolvedLink) => {
    if (item.type === 'custom') return item.url;
    return t(`pages.aiNews.links.${item.presetId}.desc`);
};

const favoriteName = (item: ResolvedLink) => {
    if (item.type === 'custom') return customTitle(item.id);
    const id = item.presetId ?? item.id;
    return t(`pages.aiNews.links.${id}.name`);
};

const markIconFailed = (key: string) => {
    iconFailed[key] = true;
};

const letterColor = (bg: string) => {
    const hex = bg.replace('#', '');
    if (hex.length !== 6) return '#fff';
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.62 ? '#303133' : '#ffffff';
};

const openLink = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
};

const onAddUrl = () => {
    const link = createCustomLinkFromUrl(urlInput.value);
    if (!link) {
        ElMessage.error(t('pages.aiNews.invalidUrl'));
        return;
    }
    if (!addCustom(link)) {
        ElMessage.warning(t('pages.aiNews.duplicateUrl'));
        return;
    }
    urlInput.value = '';
    ElMessage.success(t('pages.aiNews.added'));
};

const onDeleteLink = (item: ResolvedLink) => {
    if (item.type === 'preset') {
        hidePreset(item.id);
    } else {
        removeCustom(item.id);
    }
    ElMessage.success(t('pages.aiNews.removed'));
};

const onRemoveFavorite = (item: ResolvedLink) => {
    removeFavorite({ type: item.type, id: item.id });
};

const isFavoriteItem = (item: ResolvedLink) =>
    isFavorite({ type: item.type, id: item.id });

const onToggleFavorite = (item: ResolvedLink) => {
    const ref = { type: item.type, id: item.id };
    if (isFavorite(ref)) {
        removeFavorite(ref);
        ElMessage.success(t('pages.aiNews.unfavorited'));
        return;
    }
    if (addFavorite(ref)) {
        ElMessage.success(t('pages.aiNews.favorited'));
    }
};
</script>

<style scoped>
.ai-news-page {
    width: 100%;
}

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.page-title {
    font-size: 18px;
    font-weight: 600;
}

.page-intro {
    margin: 0 0 20px;
    font-size: 14px;
    color: #666;
    line-height: 1.6;
}

.add-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.add-bar .el-input {
    flex: 1;
}

.columns-row {
    align-items: stretch;
}

.columns-row :deep(.el-col) {
    display: flex;
}

.panel-box {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 16px;
    border: 1px solid #ebeef5;
    border-radius: 10px;
    background: #fff;
    min-height: 100%;
}

.custom-section {
    margin-top: 20px;
}

.link-section {
    height: 100%;
}

.section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 12px;
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    flex-shrink: 0;
}

.fav-icon {
    color: #e6a23c;
}

.link-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.link-list--grow {
    flex: 1;
}

.empty-hint {
    padding: 16px;
    font-size: 13px;
    color: #a8abb2;
    text-align: center;
    border: 1px dashed #dcdfe6;
    border-radius: 8px;
}

.favorites-panel {
    background: #fafcff;
}

.fav-hint {
    margin: 0 0 12px;
    font-size: 12px;
    color: #909399;
    line-height: 1.5;
    flex-shrink: 0;
}

.fav-empty {
    padding: 24px 12px;
    text-align: center;
    font-size: 13px;
    color: #a8abb2;
    border: 1px dashed #dcdfe6;
    border-radius: 8px;
}

.fav-empty--grow {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 120px;
}

.link-item--fav {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 14px;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    cursor: pointer;
    background: #fff;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.link-item--fav:hover {
    border-color: #f3d19e;
    box-shadow: 0 2px 8px rgba(230, 162, 60, 0.12);
}

.site-icon {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    object-fit: contain;
    background: #f5f7fa;
    padding: 2px;
}

.site-icon--letter {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    padding: 0;
    line-height: 1;
}

.link-info {
    flex: 1;
    min-width: 0;
}

.link-name {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 4px;
}

.link-url {
    font-size: 12px;
    color: #a8abb2;
    word-break: break-all;
}

.delete-btn {
    flex-shrink: 0;
    margin-top: 2px;
}

@media (max-width: 992px) {
    .columns-row .el-col + .el-col {
        margin-top: 20px;
    }
}
</style>
