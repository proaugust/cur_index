<template>
    <div
        class="link-item"
        :class="{ 'link-item--dragging': dragging }"
        role="link"
        tabindex="0"
        @click="emit('open', item.url)"
        @keydown.enter="emit('open', item.url)"
        @keydown.space.prevent="emit('open', item.url)"
    >
        <button
            type="button"
            class="drag-handle"
            draggable="true"
            :title="dragTitle"
            @click.stop
            @dragstart="onDragStart"
            @dragend="onDragEnd"
        >
            <el-icon><Rank /></el-icon>
        </button>
        <el-button
            class="fav-btn"
            link
            :title="favorited ? favoritedTitle : favoriteTitle"
            @click.stop="emit('favorite', item)"
        >
            <el-icon :class="{ 'fav-btn__icon--active': favorited }">
                <StarFilled v-if="favorited" />
                <Star v-else />
            </el-icon>
        </el-button>
        <div
            v-if="showLetter"
            class="site-icon site-icon--letter"
            :style="{ background: item.color, color: letterColor(item.color) }"
        >
            {{ item.letter }}
        </div>
        <img
            v-else
            :key="iconRenderKey"
            class="site-icon"
            :src="iconSrc"
            :alt="name"
            loading="lazy"
            @error="onIconError"
        />
        <div class="link-info">
            <div class="link-name">{{ name }}</div>
            <div class="link-desc">{{ desc }}</div>
            <div class="link-url">{{ item.url }}</div>
        </div>
        <el-button
            class="pin-btn"
            link
            :title="pinTitle"
            @click.stop="emit('pin-top', item)"
        >
            <el-icon><Top /></el-icon>
        </el-button>
        <el-button
            class="delete-btn"
            type="danger"
            link
            :title="deleteTitle"
            @click.stop="emit('delete', item)"
        >
            <el-icon><Delete /></el-icon>
        </el-button>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { Delete, Rank, Star, StarFilled, Top } from '@element-plus/icons-vue';
import type { AiNewsColumnId, ResolvedLink } from './ai-news-links-store';

const props = defineProps<{
    item: ResolvedLink;
    name: string;
    desc: string;
    favorited: boolean;
    column: AiNewsColumnId;
    index: number;
}>();

const emit = defineEmits<{
    open: [url: string];
    delete: [item: ResolvedLink];
    favorite: [item: ResolvedLink];
    'pin-top': [item: ResolvedLink];
    'drag-start': [payload: { key: string; column: AiNewsColumnId; index: number; event: DragEvent }];
    'drag-end': [];
}>();

const { t } = useI18n();
const FAVICON_TIMEOUT_MS = 2500;

const dragging = ref(false);
const iconSrc = ref('');
const showLetter = ref(true);
const iconRenderKey = ref(0);

const favoriteTitle = computed(() => t('pages.aiNews.clickToFavorite'));
const favoritedTitle = computed(() => t('pages.aiNews.removeFavorite'));
const deleteTitle = computed(() => t('pages.aiNews.delete'));
const pinTitle = computed(() => t('pages.aiNews.pinToTop'));
const dragTitle = computed(() => t('pages.aiNews.dragHandle'));

const shouldTryFavicon = (url: string) => {
    const trimmed = url.trim();
    if (!trimmed) return false;
    return !trimmed.includes('google.com/s2/favicons');
};

const tryLoadFavicon = () => {
    showLetter.value = true;
    iconSrc.value = '';
    const url = props.item.icon?.trim() ?? '';
    if (!shouldTryFavicon(url)) return;

    const img = new Image();
    let settled = false;
    const finish = (ok: boolean) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        if (ok) {
            iconSrc.value = url;
            showLetter.value = false;
            iconRenderKey.value += 1;
        }
    };
    const timer = window.setTimeout(() => finish(false), FAVICON_TIMEOUT_MS);
    img.onload = () => finish(true);
    img.onerror = () => finish(false);
    img.src = url;
};

onMounted(tryLoadFavicon);

watch(
    () => [props.item.key, props.item.icon] as const,
    () => {
        tryLoadFavicon();
    },
);

const onIconError = () => {
    showLetter.value = true;
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

const onDragStart = (event: DragEvent) => {
    dragging.value = true;
    event.dataTransfer?.setData(
        'application/x-ai-news-link',
        JSON.stringify({ key: props.item.key, column: props.column, index: props.index }),
    );
    if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
    }
    emit('drag-start', {
        key: props.item.key,
        column: props.column,
        index: props.index,
        event,
    });
};

const onDragEnd = () => {
    dragging.value = false;
    emit('drag-end');
};
</script>

<style scoped>
.link-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 14px 10px 14px 8px;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
}

.link-item:hover {
    border-color: #c6e2ff;
    background-color: #f5f9ff;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.08);
}

.link-item--dragging {
    opacity: 0.55;
}

.link-item:focus-visible {
    outline: 2px solid #409eff;
    outline-offset: 2px;
}

.drag-handle {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 32px;
    margin: 0;
    padding: 0;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: #c0c4cc;
    cursor: grab;
}

.drag-handle:hover {
    color: #409eff;
    background: #ecf5ff;
}

.drag-handle:active {
    cursor: grabbing;
}

.fav-btn {
    flex-shrink: 0;
    width: 28px;
    height: 32px;
    padding: 0;
    margin: 0;
    color: #c0c4cc;
}

.fav-btn:hover {
    color: #e6a23c;
}

.fav-btn__icon--active {
    color: #e6a23c;
}

.pin-btn {
    flex-shrink: 0;
    width: 28px;
    height: 32px;
    padding: 0;
    margin: 0;
    color: #909399;
}

.pin-btn:hover {
    color: #409eff;
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
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 4px;
}

.link-desc {
    font-size: 13px;
    color: #909399;
    margin-bottom: 6px;
    line-height: 1.5;
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
</style>
