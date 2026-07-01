<template>
    <div class="container zha-jinhua-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.zhaJinhua.title') }}</span>
                    <FeatureIntroIcon
                        page-key="zha-jinhua"
                        section-key="page"
                        :intros="intros"
                        :title="t('pages.zhaJinhua.title')"
                        @saved="setIntro"
                    />
                </div>
            </template>

            <div class="toolbar">
                <el-button v-if="canStartFirst" type="primary" :loading="loading" @click="handleStart">
                    {{ t('pages.zhaJinhua.start') }}
                </el-button>
                <el-button v-if="canNextRound" type="primary" :loading="loading" @click="handleNextRound">
                    {{ t('pages.zhaJinhua.nextRound') }}
                </el-button>
                <el-button type="success" :loading="simulating" :disabled="!canSimulate" @click="handleAutoRound">
                    {{ t('pages.zhaJinhua.autoRound') }}
                </el-button>
                <el-button :disabled="loading || simulating" @click="handleReset">
                    {{ t('pages.zhaJinhua.reset') }}
                </el-button>
                <el-button
                    v-if="canManageAccess"
                    :type="gameEnabled ? 'warning' : 'primary'"
                    :loading="accessLoading"
                    @click="handleToggleAccess"
                >
                    {{ gameEnabled ? t('pages.zhaJinhua.closeGame') : t('pages.zhaJinhua.openGame') }}
                </el-button>
            </div>

            <el-alert
                v-if="!gameEnabled"
                type="info"
                :title="t('pages.zhaJinhua.gameDisabledHint')"
                :closable="false"
                show-icon
                class="game-access-alert"
            />

            <div v-if="status" class="status-bar">
                <el-tag size="large" type="info">{{ t('pages.zhaJinhua.round', { n: status.round, max: status.max_rounds }) }}</el-tag>
                <el-tag size="large">{{ t('pages.zhaJinhua.phase') }}: {{ phaseLabel }}</el-tag>
            </div>

            <el-alert
                v-if="status?.phase === 'ended'"
                type="warning"
                :title="t('pages.zhaJinhua.gameOver')"
                :closable="false"
                show-icon
                class="game-over-alert"
            />

            <!-- 牌桌 -->
            <div v-if="gameStarted && status?.players" class="table-layout">
                <!-- 顶部中央：资金池（单面板 + 明细表） -->
                <div class="pot-pool">
                    <div class="pot-pool-head">
                        <el-icon class="pot-icon"><Money /></el-icon>
                        <span class="pot-title">{{ t('pages.zhaJinhua.potPool') }}</span>
                        <span class="pot-total">{{ potDisplayTotal }} {{ t('pages.zhaJinhua.yuan') }}</span>
                    </div>
                    <div v-if="potPlayerTotals.length" class="pot-summary">
                        <span class="pot-summary-label">{{ t('pages.zhaJinhua.potSummary') }}</span>
                        <span
                            v-for="item in potPlayerTotals"
                            :key="item.player_id"
                            class="pot-summary-item"
                            :style="{ borderColor: playerColor(item.player_id) }"
                        >
                            <span class="pot-summary-name" :style="{ color: playerColor(item.player_id) }">
                                {{ item.display_name }}
                            </span>
                            <span class="pot-summary-amt">{{ item.total }} {{ t('pages.zhaJinhua.yuan') }}</span>
                        </span>
                    </div>
                    <div v-if="potLedgerRows.length" class="pot-table-wrap">
                        <table class="pot-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>{{ t('pages.zhaJinhua.potPlayer') }}</th>
                                    <th>{{ t('pages.zhaJinhua.potAction') }}</th>
                                    <th>{{ t('pages.zhaJinhua.potAmount') }}</th>
                                    <th>{{ t('pages.zhaJinhua.potRunning') }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="row in potLedgerRows" :key="row.step">
                                    <td class="col-step">{{ row.step }}</td>
                                    <td class="col-player" :style="{ color: playerColor(row.player_id) }">
                                        {{ row.display_name }}
                                    </td>
                                    <td class="col-action">
                                        <span class="pot-action-tag" :class="'pot-action--' + row.actionKind">
                                            {{ row.actionLabel }}
                                        </span>
                                        <span v-if="row.tagLabel" class="pot-action-tag pot-action-tag--sub">
                                            {{ row.tagLabel }}
                                        </span>
                                    </td>
                                    <td class="col-amt">+{{ row.amount }}</td>
                                    <td class="col-running">{{ row.running }} {{ t('pages.zhaJinhua.yuan') }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div v-else class="pot-empty">{{ t('pages.zhaJinhua.potEmpty') }}</div>
                </div>

                <div class="players-row">
                    <div
                        v-for="pid in PLAYER_IDS"
                        :key="pid"
                        class="player-panel"
                        :class="{
                            active: status.current_player_id === pid && status.phase === 'betting',
                            folded: !status.players[pid]?.alive,
                            thinking: thinkingPlayer === pid,
                        }"
                    >
                        <!-- 该谁发话：放在玩家头顶 -->
                        <div
                            v-if="status.phase === 'betting' && status.players[pid]?.alive"
                            class="turn-badge"
                            :class="{ 'turn-badge--active': status.current_player_id === pid || thinkingPlayer === pid }"
                        >
                            <template v-if="thinkingPlayer === pid">
                                <el-icon class="is-loading"><Loading /></el-icon>
                                {{ t('pages.zhaJinhua.thinking') }}
                            </template>
                            <template v-else-if="status.current_player_id === pid">
                                🎤 {{ t('pages.zhaJinhua.yourTurn') }}
                            </template>
                            <template v-else>
                                {{ t('pages.zhaJinhua.waiting') }}
                            </template>
                        </div>

                        <div class="player-head">
                            <el-icon class="player-icon" :style="{ color: playerColor(pid) }"><UserFilled /></el-icon>
                            <span class="player-name">{{ status.players[pid]?.display_name }}</span>
                            <el-tag v-if="!status.players[pid]?.alive" type="info" size="small">{{ t('pages.zhaJinhua.folded') }}</el-tag>
                        </div>

                        <div class="player-meta">
                            <span class="balance">
                                {{ status.players[pid]?.balance }} {{ t('pages.zhaJinhua.yuan') }}
                            </span>
                            <span
                                v-if="(status.players[pid]?.session_pnl ?? 0) !== 0"
                                class="session-pnl"
                                :class="pnlClass(status.players[pid]?.session_pnl ?? 0)"
                            >
                                {{ t('pages.zhaJinhua.sessionPnl') }} {{ formatPnl(status.players[pid]?.session_pnl ?? 0) }}
                            </span>
                        </div>

                        <!-- 蒙牌/看牌提示 -->
                        <div class="card-mode-tag" :class="status.players[pid]?.has_looked ? 'mode-looked' : 'mode-blind'">
                            {{ status.players[pid]?.has_looked ? t('pages.zhaJinhua.looked') : t('pages.zhaJinhua.blind') }}
                        </div>

                        <!-- 手牌：观众始终可见；蒙牌=灰白，看牌=彩色 -->
                        <div class="cards-row">
                            <div
                                v-for="(card, ci) in cardList(pid)"
                                :key="ci"
                                class="card-tile"
                                :class="status.players[pid]?.has_looked ? 'card-looked' : 'card-blind'"
                            >
                                <span
                                    class="card-suit"
                                    :style="{ color: status.players[pid]?.has_looked ? suitColor(card.suit) : '#555' }"
                                >{{ suitSymbol(card.suit) }}</span>
                                <span
                                    class="card-rank"
                                    :style="{ color: status.players[pid]?.has_looked ? suitColor(card.suit) : '#333' }"
                                >{{ card.rank }}</span>
                            </div>
                        </div>
                        <div v-if="status.players[pid]?.hand_label" class="hand-label">
                            {{ status.players[pid]?.hand_label }}
                            <span class="hand-label-hint">（{{ t('pages.zhaJinhua.godView') }}）</span>
                        </div>

                        <div class="player-thought-box">
                            <div class="thought-label">
                                <el-icon class="thought-icon"><ChatDotRound /></el-icon>
                                {{ t('pages.zhaJinhua.thought') }}
                                <span v-if="thoughtHistory(pid).length" class="thought-count">
                                    ({{ thoughtHistory(pid).length }})
                                </span>
                            </div>
                            <div v-if="thoughtHistory(pid).length" class="thought-history">
                                <div
                                    v-for="(item, idx) in thoughtHistory(pid)"
                                    :key="idx"
                                    class="thought-item"
                                >
                                    <span class="thought-idx">{{ idx + 1 }}.</span>
                                    <span class="thought-text">「{{ item.text }}」</span>
                                    <span v-if="item.action" class="thought-action-tag">{{ item.action }}</span>
                                </div>
                            </div>
                            <div v-if="thinkingPlayer === pid" class="thought-content thinking-pulse">
                                {{ t('pages.zhaJinhua.thinking') }}
                            </div>
                            <div v-else-if="!thoughtHistory(pid).length" class="thought-content thought-empty">—</div>
                        </div>
                    </div>
                </div>

                <!-- 中央行动区：仅有实际行动时显示 -->
                <div v-if="centerAction" class="action-center">
                    <div class="action-center-inner" :class="'action-' + centerAction.kind">
                        <el-icon class="action-big-icon"><component :is="centerAction.icon" /></el-icon>
                        <div class="action-player">{{ centerAction.displayName }}</div>
                        <div class="action-verb">{{ centerAction.action }}</div>
                        <div v-if="centerAction.detail" class="action-detail">{{ centerAction.detail }}</div>
                    </div>
                </div>
            </div>

            <!-- 本局结算：放大 + 彩色 -->
            <div v-if="settlement" class="settlement-section">
                <div class="settlement-title">
                    <el-icon class="settlement-title-icon"><Trophy /></el-icon>
                    {{ t('pages.zhaJinhua.settlement') }}
                </div>
                <div class="settlement-winner">
                    <el-icon class="winner-icon"><Medal /></el-icon>
                    <span>{{ settlement.winner_name }}</span>
                    <span class="winner-pot">
                        {{ t('pages.zhaJinhua.netWinFromOpponents') }}
                        {{ formatPnl(settlement.winner_net_win) }} {{ t('pages.zhaJinhua.yuan') }}
                    </span>
                </div>
                <div class="settlement-grid">
                    <div v-for="pid in PLAYER_IDS" :key="'set-' + pid" class="settlement-card">
                        <div class="settlement-name">{{ settlement.players[pid]?.display_name }}</div>
                        <div class="cards-row settlement-cards">
                            <div
                                v-for="(card, ci) in parseCardsDisplay(settlement.players[pid]?.cards_display)"
                                :key="ci"
                                class="card-tile card-tile-lg"
                            >
                                <span class="card-suit" :style="{ color: suitColor(card.suit) }">{{ suitSymbol(card.suit) }}</span>
                                <span class="card-rank" :style="{ color: suitColor(card.suit) }">{{ card.rank }}</span>
                            </div>
                        </div>
                        <div class="settlement-hand">{{ settlement.players[pid]?.hand_label }}</div>
                        <div class="settlement-pnl" :class="pnlClass(settlement.players[pid]?.round_pnl ?? 0)">
                            {{ t('pages.zhaJinhua.roundPnl') }}: {{ formatPnl(settlement.players[pid]?.round_pnl ?? 0) }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- 裁判 & 系统消息 -->
            <div v-if="refereeText || systemMessages.length" class="aux-section">
                <div v-if="refereeText" class="referee-block">
                    <div class="referee-head">
                        <el-icon class="referee-icon"><Mic /></el-icon>
                        {{ t('pages.zhaJinhua.referee') }}
                    </div>
                    <div class="referee-text">{{ refereeText }}</div>
                </div>
                <div v-for="(msg, i) in systemMessages" :key="i" class="system-line">{{ msg }}</div>
            </div>

            <el-empty v-if="!gameStarted" :description="t('pages.zhaJinhua.empty')" :image-size="80" />
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-zha-jinhua">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import {
    ChatDotRound,
    Loading,
    Medal,
    Mic,
    Money,
    Switch,
    Trophy,
    UserFilled,
    View,
    Wallet,
    CloseBold,
} from '@element-plus/icons-vue';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import { usePermissStore } from '@/store/permiss';
import {
    getZhaJinhuaReferee,
    getZhaJinhuaStatus,
    nextZhaJinhuaRound,
    resetZhaJinhuaGame,
    setZhaJinhuaAccess,
    startZhaJinhuaGame,
    zhaJinhuaTurn,
} from '@/api';

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('zha-jinhua');
const permiss = usePermissStore();

type ThoughtItem = { text: string; action: string };

const PLAYER_IDS = ['Player_1', 'Player_2', 'Player_3'] as const;

const emptyThoughtHistory = (): Record<string, ThoughtItem[]> => ({
    Player_1: [],
    Player_2: [],
    Player_3: [],
});

type ParsedCard = { suit: string; rank: string; hidden: boolean };

type CenterAction = {
    kind: string;
    icon: object;
    displayName: string;
    action: string;
    detail?: string;
};

type PlayerStatus = {
    display_name: string;
    balance: number;
    alive: boolean;
    has_looked: boolean;
    cards?: string[];
    cards_display?: string;
    hand_label?: string;
    session_pnl?: number;
};

type Settlement = {
    winner_name: string;
    pot_total: number;
    winner_net_win: number;
    players: Record<string, {
        display_name: string;
        cards_display: string;
        hand_label: string;
        round_pnl: number;
    }>;
};

type PotEntry = {
    step: number;
    player_id: string;
    display_name: string;
    amount: number;
    reason: string;
};

type Status = {
    round: number;
    max_rounds: number;
    pot: number;
    phase: string;
    game_enabled?: boolean;
    current_player_id?: string | null;
    last_settlement?: Settlement | null;
    pot_ledger?: PotEntry[];
    players: Record<string, PlayerStatus>;
};

const PLAYER_COLORS: Record<string, string> = {
    Player_1: '#e74c3c',
    Player_2: '#3498db',
    Player_3: '#9b59b6',
};

const SUIT_SYMBOLS: Record<string, string> = { H: '♥', D: '♦', C: '♣', S: '♠' };
const SUIT_COLORS: Record<string, string> = {
    H: '#e74c3c',
    D: '#e67e22',
    C: '#27ae60',
    S: '#2980b9',
};

const loading = ref(false);
const accessLoading = ref(false);
const simulating = ref(false);
const status = ref<Status | null>(null);
const playerThoughtHistory = ref<Record<string, ThoughtItem[]>>(emptyThoughtHistory());
const thinkingPlayer = ref<string | null>(null);
const centerAction = ref<CenterAction | null>(null);
const refereeText = ref('');
const systemMessages = ref<string[]>([]);

const phaseLabel = computed(() => {
    const p = status.value?.phase ?? 'idle';
    const map: Record<string, string> = {
        idle: t('pages.zhaJinhua.phaseIdle'),
        betting: t('pages.zhaJinhua.phaseBetting'),
        round_end: t('pages.zhaJinhua.phaseRoundEnd'),
        ended: t('pages.zhaJinhua.phaseEnded'),
    };
    return map[p] ?? p;
});

const gameStarted = computed(() => (status.value?.phase ?? 'idle') !== 'idle');
const gameEnabled = computed(() => status.value?.game_enabled ?? false);
const canManageAccess = computed(() => permiss.has('89.access'));
const canStartFirst = computed(
    () => gameEnabled.value && status.value?.phase === 'idle' && !simulating.value,
);
const canNextRound = computed(
    () =>
        gameEnabled.value
        && status.value?.phase === 'round_end'
        && (status.value?.round ?? 0) < (status.value?.max_rounds ?? 10)
        && !simulating.value,
);
const canSimulate = computed(() => gameEnabled.value && status.value?.phase === 'betting' && !simulating.value);
const settlement = computed(() => status.value?.last_settlement ?? null);

type PotLedgerRow = PotEntry & {
    actionLabel: string;
    actionKind: string;
    tagLabel: string;
    running: number;
};

const parsePotReason = (reason: string) => {
    if (reason === '底分') return { actionLabel: t('pages.zhaJinhua.ante'), actionKind: 'ante', tagLabel: '' };
    if (reason.startsWith('跟注/')) {
        const tag = reason.split('/')[1] ?? '';
        return { actionLabel: t('pages.zhaJinhua.call'), actionKind: 'call', tagLabel: tag };
    }
    if (reason.startsWith('加注/')) {
        const tag = reason.split('/')[1] ?? '';
        return { actionLabel: t('pages.zhaJinhua.raise'), actionKind: 'raise', tagLabel: tag };
    }
    if (reason === '比牌') return { actionLabel: t('pages.zhaJinhua.compare'), actionKind: 'compare', tagLabel: '' };
    return { actionLabel: reason, actionKind: 'default', tagLabel: '' };
};

const potLedgerRows = computed((): PotLedgerRow[] => {
    const ledger = status.value?.pot_ledger ?? [];
    let running = 0;
    return ledger.map((entry) => {
        running += entry.amount;
        const parsed = parsePotReason(entry.reason);
        return { ...entry, ...parsed, running };
    });
});

/** 与明细表「池内累计」最后一行保持一致 */
const potDisplayTotal = computed(() => {
    const rows = potLedgerRows.value;
    if (rows.length > 0) return rows[rows.length - 1].running;
    return status.value?.pot ?? 0;
});

const potPlayerTotals = computed(() => {
    const totals = new Map<string, { player_id: string; display_name: string; total: number }>();
    for (const entry of status.value?.pot_ledger ?? []) {
        const prev = totals.get(entry.player_id);
        if (prev) {
            prev.total += entry.amount;
        } else {
            totals.set(entry.player_id, {
                player_id: entry.player_id,
                display_name: entry.display_name,
                total: entry.amount,
            });
        }
    }
    return PLAYER_IDS.map((pid) => totals.get(pid)).filter(Boolean) as {
        player_id: string;
        display_name: string;
        total: number;
    }[];
});

const thoughtHistory = (pid: string) => playerThoughtHistory.value[pid] ?? [];

const appendThought = (playerId: string, text: string, action: string) => {
    const prev = playerThoughtHistory.value[playerId] ?? [];
    playerThoughtHistory.value = {
        ...playerThoughtHistory.value,
        [playerId]: [...prev, { text: text || '……', action }],
    };
};

const playerDisplay = (pid: string) => status.value?.players[pid]?.display_name ?? pid;
const playerColor = (pid: string) => PLAYER_COLORS[pid] ?? '#606266';
const suitSymbol = (s: string) => SUIT_SYMBOLS[s] ?? s;
const suitColor = (s: string) => SUIT_COLORS[s] ?? '#303133';
const formatPnl = (n: number) => (n > 0 ? `+${n}` : `${n}`);
const pnlClass = (n: number) => (n > 0 ? 'pnl-win' : n < 0 ? 'pnl-lose' : '');

/** 后端用 T 表示 10，前端展示为 10；A/J/Q/K 保持原样 */
const formatRankDisplay = (rank: string): string => {
    if (rank === 'T') return '10';
    return rank;
};

const parseRawCard = (raw: string): ParsedCard => {
    if (!raw || raw === '?') return { suit: '', rank: '?', hidden: true };
    const suit = raw[0];
    const rank = formatRankDisplay(raw.slice(1));
    return { suit, rank, hidden: false };
};

const cardList = (pid: string): ParsedCard[] => {
    const cards = status.value?.players[pid]?.cards;
    if (!cards?.length) {
        return [{ hidden: true, suit: '', rank: '-' }, { hidden: true, suit: '', rank: '-' }, { hidden: true, suit: '', rank: '-' }];
    }
    return cards.map(parseRawCard).filter((c) => c.rank !== '?');
};

const parseCardsDisplay = (display?: string): ParsedCard[] => {
    if (!display) return [];
    return display.split(/\s+/).map((part) => {
        const suitChar = part[0];
        const suitKey = { '♥': 'H', '♦': 'D', '♣': 'C', '♠': 'S' }[suitChar] ?? suitChar;
        return { suit: suitKey, rank: formatRankDisplay(part.slice(1)), hidden: false };
    });
};

const actionIcon = (action: string) => {
    if (action.includes('看牌')) return View;
    if (action.includes('跟注')) return Money;
    if (action.includes('加注')) return Wallet;
    if (action.includes('比牌')) return Switch;
    if (action.includes('弃牌')) return CloseBold;
    return Money;
};

const actionKind = (action: string) => {
    if (action.includes('看牌')) return 'look';
    if (action.includes('跟注')) return 'call';
    if (action.includes('加注')) return 'raise';
    if (action.includes('比牌')) return 'compare';
    if (action.includes('弃牌')) return 'fold';
    return 'default';
};

const setCenterAction = (displayName: string, action: string, amount: number, target?: string) => {
    let detail = '';
    if (amount > 0) detail = `${t('pages.zhaJinhua.amount')}: ${amount}元`;
    if (target) detail = detail ? `${detail} → ${target}` : target;
    centerAction.value = {
        kind: actionKind(action),
        icon: actionIcon(action),
        displayName,
        action,
        detail: detail || undefined,
    };
};

const refreshStatus = async () => {
    const res = await getZhaJinhuaStatus();
    status.value = res.data;
};

const showError = (err: unknown) => {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(typeof msg === 'string' ? msg : t('pages.zhaJinhua.error'));
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const clearRoundUi = () => {
    playerThoughtHistory.value = emptyThoughtHistory();
    thinkingPlayer.value = null;
    centerAction.value = null;
    refereeText.value = '';
};

const handleStart = async () => {
    loading.value = true;
    try {
        clearRoundUi();
        systemMessages.value = [];
        const res = await startZhaJinhuaGame();
        systemMessages.value.push(res.data.message);
        await refreshStatus();
    } catch (err) {
        showError(err);
    } finally {
        loading.value = false;
    }
};

const handleNextRound = async () => {
    loading.value = true;
    try {
        clearRoundUi();
        const res = await nextZhaJinhuaRound();
        systemMessages.value.push(res.data.message);
        await refreshStatus();
    } catch (err) {
        showError(err);
    } finally {
        loading.value = false;
    }
};

const handleReset = async () => {
    loading.value = true;
    try {
        clearRoundUi();
        systemMessages.value = [];
        const res = await resetZhaJinhuaGame();
        systemMessages.value = [res.data.message];
        await refreshStatus();
    } catch (err) {
        showError(err);
    } finally {
        loading.value = false;
    }
};

const handleToggleAccess = async () => {
    accessLoading.value = true;
    try {
        const res = await setZhaJinhuaAccess(!gameEnabled.value);
        systemMessages.value.push(res.data.message);
        await refreshStatus();
        ElMessage.success(res.data.message);
    } catch (err) {
        showError(err);
    } finally {
        accessLoading.value = false;
    }
};

const runOneTurn = async (playerId: string) => {
    thinkingPlayer.value = playerId;
    centerAction.value = null;
    await sleep(350);

    const res = await zhaJinhuaTurn(playerId);
    const data = res.data;
    thinkingPlayer.value = null;

    if (data.skipped) {
        systemMessages.value.push(`【${data.display_name}】${data.reason || t('pages.zhaJinhua.skipped')}`);
    } else {
        appendThought(playerId, data.thought || '……', data.action);
        setCenterAction(data.display_name, data.action, data.amount ?? 0, data.target || undefined);
    }
    await refreshStatus();
    return data;
};

const handleAutoRound = async () => {
    if (!canSimulate.value) return;
    simulating.value = true;
    try {
        await refreshStatus();
        let guard = 0;
        let hadAction = false;
        while (status.value?.phase === 'betting' && guard < 24) {
            guard += 1;
            const current = status.value?.current_player_id;
            if (!current) break;
            const data = await runOneTurn(current);
            if (!data.skipped) hadAction = true;
        }

        if (hadAction) {
            thinkingPlayer.value = '__referee__';
            centerAction.value = null;
            await sleep(600);
            const refRes = await getZhaJinhuaReferee();
            refereeText.value = refRes.data.referee_voice;
            thinkingPlayer.value = null;
            await refreshStatus();
        }

        if (status.value?.phase === 'round_end') {
            systemMessages.value.push(t('pages.zhaJinhua.roundEndHint'));
        }
        if (status.value?.phase === 'ended') {
            systemMessages.value.push(t('pages.zhaJinhua.allEndHint'));
        }
    } catch (err) {
        showError(err);
        thinkingPlayer.value = null;
    } finally {
        simulating.value = false;
    }
};

watch(
    () => status.value?.phase,
    (phase) => {
        if (phase === 'idle') clearRoundUi();
    },
);

refreshStatus().catch(() => undefined);
</script>

<style scoped>
.zha-jinhua-page .page-header {
    display: inline-flex;
    align-items: center;
}

.zha-jinhua-page .page-title {
    font-size: 16px;
    font-weight: 600;
}

.toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.status-bar {
    margin-top: 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.game-over-alert {
    margin-top: 12px;
}

.game-access-alert {
    margin-top: 12px;
}

/* ── 资金池（单面板 + 明细表） ── */
.pot-pool {
    width: 100%;
    margin: 0 0 8px;
    padding: 16px 20px 14px;
    border-radius: 14px;
    border: 3px solid #f39c12;
    background: linear-gradient(180deg, #fef5e7 0%, #fff 100%);
}

.pot-pool-head {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
}

.pot-icon {
    font-size: 32px;
    color: #f39c12;
}

.pot-title {
    font-size: 22px;
    font-weight: 800;
    color: #d35400;
}

.pot-total {
    font-size: 32px;
    font-weight: 800;
    color: var(--el-color-success);
}

.pot-summary {
    margin-top: 12px;
    padding: 10px 14px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 10px 16px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.85);
    border: 1px dashed #f5cba7;
}

.pot-summary-label {
    font-size: 13px;
    font-weight: 700;
    color: var(--el-text-color-secondary);
}

.pot-summary-item {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    border-radius: 8px;
    border-left: 4px solid #ccc;
    background: #fff;
}

.pot-summary-name {
    font-size: 14px;
    font-weight: 700;
}

.pot-summary-amt {
    font-size: 16px;
    font-weight: 800;
    color: var(--el-color-success);
}

.pot-table-wrap {
    margin-top: 12px;
    border-radius: 10px;
    overflow: hidden;
    border: 2px solid #f5cba7;
    background: #fff;
}

.pot-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

.pot-table thead {
    background: #fdebd0;
}

.pot-table th {
    padding: 10px 12px;
    font-weight: 700;
    color: #7e5109;
    text-align: left;
    white-space: nowrap;
}

.pot-table td {
    padding: 9px 12px;
    border-top: 1px solid #f5e6d3;
    vertical-align: middle;
}

.pot-table tbody tr:nth-child(even) {
    background: #fffcf7;
}

.pot-table tbody tr:hover {
    background: #fef5e7;
}

.col-step {
    width: 48px;
    color: var(--el-text-color-secondary);
    font-weight: 600;
}

.col-player {
    font-weight: 700;
    min-width: 120px;
}

.col-action {
    min-width: 120px;
}

.col-amt {
    font-weight: 800;
    color: var(--el-color-success);
    white-space: nowrap;
}

.col-running {
    font-weight: 700;
    color: #d35400;
    white-space: nowrap;
}

.pot-action-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 700;
}

.pot-action-tag--sub {
    margin-left: 4px;
    font-weight: 600;
    opacity: 0.85;
}

.pot-action--ante {
    background: #ecf0f1;
    color: #566573;
}

.pot-action--call {
    background: #d6eaf8;
    color: #1a5276;
}

.pot-action--raise {
    background: #fadbd8;
    color: #922b21;
}

.pot-action--compare {
    background: #e8daef;
    color: #6c3483;
}

.pot-action--default {
    background: #f4f6f7;
    color: #566573;
}

.pot-empty {
    margin-top: 10px;
    text-align: center;
    font-size: 13px;
    color: var(--el-text-color-placeholder);
}

/* ── 牌桌布局 ── */
.table-layout {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.players-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}

@media (max-width: 900px) {
    .players-row {
        grid-template-columns: 1fr;
    }
}

.player-panel {
    padding: 16px;
    border-radius: 12px;
    border: 2px solid var(--el-border-color-light);
    background: var(--el-fill-color-blank);
    transition: border-color 0.25s, box-shadow 0.25s;
}

.player-panel.active {
    border-color: var(--el-color-success);
    box-shadow: 0 0 0 3px rgba(103, 194, 58, 0.15);
}

.player-panel.thinking {
    border-color: var(--el-color-warning);
    box-shadow: 0 0 0 3px rgba(230, 162, 60, 0.2);
}

.player-panel.folded {
    opacity: 0.55;
}

.turn-badge {
    text-align: center;
    padding: 6px 10px;
    margin: -8px -8px 10px;
    border-radius: 8px 8px 0 0;
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
    background: var(--el-fill-color-light);
}

.turn-badge--active {
    background: linear-gradient(90deg, #fff3cd, #ffeaa7);
    color: #d35400;
    font-size: 15px;
    animation: turn-glow 1.5s ease-in-out infinite;
}

@keyframes turn-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(243, 156, 18, 0.3); }
    50% { box-shadow: 0 0 12px 2px rgba(243, 156, 18, 0.45); }
}

.card-mode-tag {
    text-align: center;
    font-size: 12px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
    display: inline-block;
    width: 100%;
}

.mode-blind {
    background: #ececec;
    color: #666;
}

.mode-looked {
    background: #e8f8f5;
    color: #1abc9c;
}

.card-blind {
    background: #f5f5f5 !important;
    border-color: #bbb !important;
    filter: grayscale(100%);
}

.card-looked {
    background: #fff !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.hand-label-hint {
    font-size: 11px;
    font-weight: 400;
    color: var(--el-text-color-secondary);
}

.player-head {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
}

.player-icon {
    font-size: 28px;
}

.player-name {
    font-size: 16px;
    font-weight: 700;
}

.player-meta {
    display: flex;
    gap: 12px;
    font-size: 14px;
    margin-bottom: 12px;
}

.balance {
    color: var(--el-color-primary);
    font-weight: 600;
}

.session-pnl {
    font-weight: 600;
}

/* ── 手牌：2 倍大号彩色 ── */
.cards-row {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin-bottom: 8px;
}

.card-tile {
    width: 64px;
    height: 88px;
    border-radius: 10px;
    border: 2px solid var(--el-border-color);
    background: #fff;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
}

.card-tile.hidden {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-color: #5a67d8;
}

.card-tile-lg {
    width: 72px;
    height: 98px;
}

.card-suit {
    font-size: 36px;
    line-height: 1;
    font-weight: 700;
}

.card-rank {
    font-size: 22px;
    font-weight: 800;
    line-height: 1.1;
}

.card-tile.hidden .card-rank {
    color: #fff;
    font-size: 26px;
}

.card-back-icon {
    font-size: 32px;
    color: rgba(255, 255, 255, 0.85);
    margin-bottom: 2px;
}

.hand-label {
    text-align: center;
    font-size: 14px;
    font-weight: 600;
    color: var(--el-color-warning);
    margin-bottom: 8px;
}

/* ── 内心独白（牌下方） ── */
.player-thought-box {
    margin-top: 4px;
    padding: 10px 12px;
    border-radius: 8px;
    background: var(--el-fill-color-light);
    border-left: 4px solid var(--el-color-warning);
    min-height: 56px;
}

.thought-count {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    font-weight: 400;
}

.thought-history {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: none;
}

.thought-item {
    font-size: 13px;
    line-height: 1.55;
    padding: 6px 8px;
    border-radius: 6px;
    background: var(--el-fill-color-blank);
    border: 1px solid var(--el-border-color-lighter);
}

.thought-idx {
    color: var(--el-text-color-secondary);
    font-weight: 600;
    margin-right: 4px;
}

.thought-text {
    color: var(--el-text-color-regular);
}

.thought-action-tag {
    display: inline-block;
    margin-left: 6px;
    padding: 1px 6px;
    font-size: 11px;
    font-weight: 700;
    border-radius: 4px;
    background: var(--el-color-success-light-9);
    color: var(--el-color-success);
}

.thought-label {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    font-weight: 600;
    color: var(--el-color-warning);
    margin-bottom: 6px;
}

.thought-icon {
    font-size: 18px;
}

.thought-content {
    font-size: 14px;
    line-height: 1.65;
    color: var(--el-text-color-regular);
}

.thought-empty {
    color: var(--el-text-color-placeholder);
}

.thinking-pulse {
    margin-top: 8px;
    color: var(--el-color-warning);
    font-weight: 600;
    animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.45; }
}

/* ── 中央行动区 ── */
.action-center {
    display: flex;
    justify-content: center;
    padding: 8px 0;
}

.action-center-inner {
    min-width: 280px;
    max-width: 420px;
    width: 100%;
    padding: 24px 32px;
    border-radius: 16px;
    text-align: center;
    border: 3px solid var(--el-border-color);
    background: var(--el-fill-color-blank);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
}

.action-big-icon {
    font-size: 56px;
    margin-bottom: 8px;
}

.action-call .action-big-icon { color: #3498db; }
.action-raise .action-big-icon { color: #e74c3c; }
.action-look .action-big-icon { color: #9b59b6; }
.action-compare .action-big-icon { color: #e67e22; }
.action-fold .action-big-icon { color: #95a5a6; }
.action-thinking .action-big-icon { color: var(--el-color-warning); }

.action-call { border-color: #3498db; background: linear-gradient(180deg, #ebf5fb 0%, #fff 100%); }
.action-raise { border-color: #e74c3c; background: linear-gradient(180deg, #fdedec 0%, #fff 100%); }
.action-look { border-color: #9b59b6; background: linear-gradient(180deg, #f5eef8 0%, #fff 100%); }
.action-compare { border-color: #e67e22; background: linear-gradient(180deg, #fef5e7 0%, #fff 100%); }
.action-fold { border-color: #95a5a6; background: linear-gradient(180deg, #f4f6f7 0%, #fff 100%); }

.action-player {
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin-bottom: 4px;
}

.action-verb {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: 2px;
}

.action-call .action-verb { color: #2980b9; }
.action-raise .action-verb { color: #c0392b; }
.action-look .action-verb { color: #8e44ad; }
.action-compare .action-verb { color: #d35400; }
.action-fold .action-verb { color: #7f8c8d; }

.action-detail {
    margin-top: 8px;
    font-size: 18px;
    font-weight: 600;
    color: var(--el-text-color-regular);
}

/* ── 结算区：放大 + 彩色 ── */
.settlement-section {
    margin-top: 24px;
    padding: 20px;
    border-radius: 14px;
    border: 3px solid var(--el-color-warning);
    background: linear-gradient(180deg, #fef9e7 0%, var(--el-fill-color-blank) 100%);
}

.settlement-title {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 24px;
    font-weight: 800;
    color: var(--el-color-warning);
    margin-bottom: 16px;
}

.settlement-title-icon {
    font-size: 32px;
    color: #f39c12;
}

.settlement-winner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 20px;
    padding: 12px;
    border-radius: 10px;
    background: rgba(243, 156, 18, 0.12);
}

.winner-icon {
    font-size: 36px;
    color: #f1c40f;
}

.winner-pot {
    color: var(--el-color-success);
    font-size: 26px;
}

.settlement-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}

@media (max-width: 900px) {
    .settlement-grid {
        grid-template-columns: 1fr;
    }
}

.settlement-card {
    padding: 16px;
    border-radius: 12px;
    border: 2px solid var(--el-border-color-light);
    background: #fff;
    text-align: center;
}

.settlement-name {
    font-size: 17px;
    font-weight: 700;
    margin-bottom: 10px;
}

.settlement-cards {
    margin-bottom: 8px;
}

.settlement-hand {
    font-size: 16px;
    font-weight: 600;
    color: var(--el-color-warning);
    margin-bottom: 6px;
}

.settlement-pnl {
    font-size: 20px;
    font-weight: 800;
}

.pnl-win {
    color: var(--el-color-success);
}

.pnl-lose {
    color: var(--el-color-danger);
}

/* ── 裁判 & 系统 ── */
.aux-section {
    margin-top: 20px;
}

.referee-block {
    padding: 16px;
    border-radius: 10px;
    border-left: 4px solid var(--el-color-danger);
    background: var(--el-fill-color-light);
    margin-bottom: 12px;
}

.referee-head {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 16px;
    font-weight: 700;
    color: var(--el-color-danger);
    margin-bottom: 8px;
}

.referee-icon {
    font-size: 22px;
}

.referee-text {
    font-size: 15px;
    line-height: 1.75;
    white-space: pre-wrap;
}

.system-line {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    padding: 4px 0;
}
</style>
