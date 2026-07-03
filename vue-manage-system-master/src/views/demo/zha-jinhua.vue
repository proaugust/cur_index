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
                <el-tag v-if="status.phase === 'betting'" size="large" type="warning">
                    {{ t('pages.zhaJinhua.actionProgress', { n: status.actions_this_round ?? 0, max: status.max_actions_per_round ?? 24 }) }}
                </el-tag>
                <el-tag v-if="status.early_showdown" size="large" type="danger">
                    {{ t('pages.zhaJinhua.earlyShowdown') }}
                </el-tag>
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
                <!-- 本局资金池（下注中 + 局末保留，下一局开始时清空） -->
                <div v-if="showRoundPotLedger" class="pot-pool">
                    <div class="pot-pool-head">
                        <el-icon class="pot-icon"><Money /></el-icon>
                        <span class="pot-title">{{ t('pages.zhaJinhua.potPool') }}</span>
                        <span class="pot-total">{{ potDisplayTotal }} {{ t('pages.zhaJinhua.yuan') }}</span>
                    </div>
                    <div class="pot-summary">
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
                    <ZhaJinhuaPotLedgerTable
                        v-if="potLedgerRows.length"
                        :rows="potLedgerRows"
                        :row-key-prefix="`r${status.round}`"
                        :player-color="playerColor"
                    />
                    <div v-else class="pot-empty">{{ t('pages.zhaJinhua.potEmpty') }}</div>
                </div>

                <div class="players-row">
                    <div
                        v-for="pid in PLAYER_IDS"
                        :key="`r${status.round}-${pid}`"
                        class="player-slot"
                        :class="{ 'player-slot--betting': status.phase === 'betting' }"
                    >
                        <!-- 该谁发话：绝对定位在预留区内，切换时不挤压面板 -->
                        <div
                            v-if="status.phase === 'betting' && status.players[pid]?.alive && status.current_player_id === pid"
                            class="turn-mic-float"
                        >
                            🎤 {{ t('pages.zhaJinhua.yourTurn') }}
                        </div>

                        <div
                            class="player-panel"
                            :class="{
                                active: status.current_player_id === pid && status.phase === 'betting',
                                folded: !status.players[pid]?.alive,
                                thinking: thinkingPlayer === pid,
                            }"
                        >
                            <div
                                v-if="status.phase === 'betting' && status.players[pid]?.alive && thinkingPlayer === pid"
                                class="thinking-badge"
                            >
                                <el-icon class="is-loading"><Loading /></el-icon>
                                {{ t('pages.zhaJinhua.thinking') }}
                            </div>
                            <div
                                v-else-if="status.phase === 'betting' && status.players[pid]?.alive && status.current_player_id !== pid"
                                class="status-badge"
                            >
                                {{ t('pages.zhaJinhua.waiting') }}
                            </div>

                        <!-- 实际行动：右上角角标 -->
                        <div
                            v-if="playerLastAction[pid]"
                            class="player-action-badge"
                            :class="'action-' + playerLastAction[pid]!.kind"
                        >
                            <el-icon class="action-badge-icon"><component :is="playerLastAction[pid]!.icon" /></el-icon>
                            <span class="action-badge-verb">{{ playerLastAction[pid]!.action }}</span>
                            <span v-if="playerLastAction[pid]!.detail" class="action-badge-detail">
                                {{ playerLastAction[pid]!.detail }}
                            </span>
                        </div>

                        <div class="player-head">
                            <el-icon class="player-icon" :style="{ color: playerColor(pid) }"><UserFilled /></el-icon>
                            <span class="player-name">{{ status.players[pid]?.display_name }}</span>
                            <el-tag v-if="!status.players[pid]?.alive" type="info" size="small">{{ t('pages.zhaJinhua.folded') }}</el-tag>
                            <el-tag v-else-if="status.players[pid]?.all_in" type="warning" size="small">{{ t('pages.zhaJinhua.allIn') }}</el-tag>
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
                                <span v-if="thoughtsFor(pid).length" class="thought-count">
                                    ({{ thoughtsFor(pid).length }})
                                </span>
                            </div>
                            <div v-if="thoughtsFor(pid).length" class="thought-history">
                                <div
                                    v-for="(item, idx) in thoughtsFor(pid)"
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
                            <div v-else-if="!thoughtsFor(pid).length" class="thought-content thought-empty">—</div>
                        </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 本局结算：放大 + 彩色 -->
            <div v-if="settlement" class="settlement-section">
                <div class="settlement-title">
                    <el-icon class="settlement-title-icon"><Trophy /></el-icon>
                    {{ t('pages.zhaJinhua.settlement') }}
                    <span class="settlement-pot-total">
                        {{ t('pages.zhaJinhua.potPool') }} {{ potDisplayTotal }} {{ t('pages.zhaJinhua.yuan') }}
                    </span>
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
import { computed, nextTick, ref, watch } from 'vue';
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
import ZhaJinhuaPotLedgerTable, { type PotLedgerRow } from './zha-jinhua-pot-ledger-table.vue';
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
const MAX_AUTO_TURNS_ABS = 50;
/** 本手行动与列表展示后，再切下一家 */
const TURN_LEDGER_PAUSE_MS = 220;

const emptyThoughtHistory = (): Record<string, ThoughtItem[]> => ({
    Player_1: [],
    Player_2: [],
    Player_3: [],
});

const emptyPlayerActions = (): Record<string, PlayerAction | null> => ({
    Player_1: null,
    Player_2: null,
    Player_3: null,
});

type ParsedCard = { suit: string; rank: string };

type PlayerAction = {
    kind: string;
    icon: object;
    action: string;
    detail?: string;
};

type PlayerStatus = {
    display_name: string;
    balance: number;
    alive: boolean;
    has_looked: boolean;
    all_in?: boolean;
    cards?: string[];
    cards_display?: string;
    hand_label?: string;
    session_pnl?: number;
};

type Settlement = {
    winner_name: string;
    pot_total: number;
    winner_net_win: number;
    pot_ledger?: PotEntry[];
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
    pot_after?: number;
    line_stake?: number;
};

type Status = {
    round: number;
    max_rounds: number;
    pot: number;
    phase: string;
    early_showdown?: boolean;
    game_enabled?: boolean;
    current_player_id?: string | null;
    actions_this_round?: number;
    max_actions_per_round?: number;
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
/** 丢弃过期的 GET /status 响应，避免并发刷新互相覆盖 */
let statusFetchSeq = 0;
const playerThoughtHistory = ref<Record<string, ThoughtItem[]>>(emptyThoughtHistory());
const playerLastAction = ref<Record<string, PlayerAction | null>>(emptyPlayerActions());
const thinkingPlayer = ref<string | null>(null);
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
const showRoundPotLedger = computed(() => {
    const phase = status.value?.phase;
    return phase === 'betting' || phase === 'round_end' || phase === 'ended';
});

const parseBetTag = (raw: string) => {
    if (raw.includes('明注')) {
        return { tagLabel: t('pages.zhaJinhua.betOpen'), betKind: 'open' as const };
    }
    if (raw.includes('暗注')) {
        return { tagLabel: t('pages.zhaJinhua.betBlind'), betKind: 'blind' as const };
    }
    return { tagLabel: raw, betKind: '' as const };
};

const parsePotReason = (reason: string) => {
    const emptyBet = { tagLabel: '', betKind: '' as const, extraTag: '' };
    if (reason === '底分') {
        return { actionLabel: t('pages.zhaJinhua.ante'), actionKind: 'ante', ...emptyBet };
    }
    if (reason.startsWith('跟注/')) {
        const parts = reason.split('/');
        const { tagLabel, betKind } = parseBetTag(parts[1] ?? '');
        return {
            actionLabel: t('pages.zhaJinhua.call'),
            actionKind: 'call',
            tagLabel,
            betKind,
            extraTag: parts.includes('全下') ? t('pages.zhaJinhua.allIn') : '',
        };
    }
    if (reason.startsWith('加注/')) {
        const parts = reason.split('/');
        const { tagLabel, betKind } = parseBetTag(parts[1] ?? '');
        return {
            actionLabel: t('pages.zhaJinhua.raise'),
            actionKind: 'raise',
            tagLabel,
            betKind,
            extraTag: parts.includes('全下') ? t('pages.zhaJinhua.allIn') : '',
        };
    }
    if (reason.startsWith('比牌/')) {
        const parts = reason.split('/');
        const { tagLabel, betKind } = parseBetTag(parts[1] ?? '');
        return {
            actionLabel: t('pages.zhaJinhua.compare'),
            actionKind: 'compare',
            tagLabel,
            betKind,
            extraTag: parts.includes('全下') ? t('pages.zhaJinhua.allIn') : '',
        };
    }
    if (reason === '比牌') {
        return { actionLabel: t('pages.zhaJinhua.compare'), actionKind: 'compare', ...emptyBet };
    }
    if (reason === '弃牌') {
        return { actionLabel: t('pages.zhaJinhua.fold'), actionKind: 'fold', ...emptyBet };
    }
    if (reason === '开牌' || reason.startsWith('开牌/')) {
        return { actionLabel: t('pages.zhaJinhua.showdown'), actionKind: 'showdown', ...emptyBet };
    }
    return { actionLabel: reason, actionKind: 'default', ...emptyBet };
};

const potLedgerRows = computed((): PotLedgerRow[] => buildPotLedgerRows(activePotLedger.value));

/** 本局入池明细唯一数据源（下注中 / 局末 / 整局结束均用 status.pot_ledger） */
const activePotLedger = computed((): PotEntry[] => status.value?.pot_ledger ?? []);

/** 入池金额统一数值化，避免 API/合并后字符串拼接（如 10+'10'→'1010'） */
const ledgerEntryAmount = (entry: Pick<PotEntry, 'amount'>): number => {
    const n = Number(entry.amount);
    return Number.isFinite(n) ? n : 0;
};

const sumLedgerAmounts = (ledger: PotEntry[]): number =>
    ledger.reduce((sum, entry) => sum + ledgerEntryAmount(entry), 0);

function buildPotLedgerRows(ledger: PotEntry[]): PotLedgerRow[] {
    let poolRunning = 0;
    const playerRunning = new Map<string, number>();
    return ledger.map((entry) => {
        const amount = ledgerEntryAmount(entry);
        poolRunning += amount;
        const prevPlayer = playerRunning.get(entry.player_id) ?? 0;
        const nextPlayer = prevPlayer + amount;
        playerRunning.set(entry.player_id, nextPlayer);
        const parsed = parsePotReason(entry.reason);
        const lineStake = Number(entry.line_stake) || amount;
        const atLine = amount === 0
            && lineStake > 0
            && (parsed.actionKind === 'call' || parsed.actionKind === 'raise' || parsed.actionKind === 'compare');
        return {
            step: entry.step,
            player_id: entry.player_id,
            display_name: entry.display_name,
            amount,
            line_stake: lineStake,
            running: poolRunning,
            playerRunning: nextPlayer,
            atLine,
            ...parsed,
        };
    });
}

/** 奖池总额 = ledger 入池金额之和 = 末行池内累计 = 各玩家入池合计之和 */
const potDisplayTotal = computed(() => sumLedgerAmounts(activePotLedger.value));

const potPlayerTotals = computed(() => {
    const totals = new Map<string, { player_id: string; display_name: string; total: number }>();
    for (const entry of activePotLedger.value) {
        const inc = ledgerEntryAmount(entry);
        const prev = totals.get(entry.player_id);
        if (prev) {
            prev.total += inc;
        } else {
            totals.set(entry.player_id, {
                player_id: entry.player_id,
                display_name: entry.display_name,
                total: inc,
            });
        }
    }
    return PLAYER_IDS.map((pid) => {
        const found = totals.get(pid);
        if (found) return found;
        return {
            player_id: pid,
            display_name: status.value?.players[pid]?.display_name ?? pid,
            total: 0,
        };
    });
});

const thoughtsFor = (pid: string) => playerThoughtHistory.value[pid] ?? [];

const appendThought = (playerId: string, text: string, action: string) => {
    const prev = playerThoughtHistory.value[playerId] ?? [];
    playerThoughtHistory.value = {
        ...playerThoughtHistory.value,
        [playerId]: [...prev, { text: text || '……', action }],
    };
};

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

const parseRawCard = (raw: string): ParsedCard | null => {
    if (!raw || raw === '?') return null;
    const suit = raw[0];
    const rank = formatRankDisplay(raw.slice(1));
    return { suit, rank };
};

const cardList = (pid: string): ParsedCard[] => {
    const cards = status.value?.players[pid]?.cards;
    if (!cards?.length) {
        return [
            { suit: '', rank: '-' },
            { suit: '', rank: '-' },
            { suit: '', rank: '-' },
        ];
    }
    const parsed = cards.map(parseRawCard).filter((c): c is ParsedCard => c !== null);
    return parsed.length ? parsed : [
        { suit: '', rank: '-' },
        { suit: '', rank: '-' },
        { suit: '', rank: '-' },
    ];
};

const parseCardsDisplay = (display?: string): ParsedCard[] => {
    if (!display) return [];
    return display.split(/\s+/).map((part) => {
        const suitChar = part[0];
        const suitKey = { '♥': 'H', '♦': 'D', '♣': 'C', '♠': 'S' }[suitChar] ?? suitChar;
        return { suit: suitKey, rank: formatRankDisplay(part.slice(1)) };
    });
};

const parseActionMeta = (action: string) => {
    if (action.includes('看牌')) return { kind: 'look', icon: View };
    if (action.includes('跟注')) return { kind: 'call', icon: Money };
    if (action.includes('加注')) return { kind: 'raise', icon: Wallet };
    if (action.includes('比牌')) return { kind: 'compare', icon: Switch };
    if (action.includes('弃牌')) return { kind: 'fold', icon: CloseBold };
    return { kind: 'default', icon: Money };
};

const setPlayerAction = (
    playerId: string,
    action: string,
    amount: number,
    target?: string,
    justLooked?: boolean,
    betTag?: string,
) => {
    let detail = '';
    const paid = Number(amount) || 0;
    if (paid > 0) {
        detail = `+${paid}`;
    }
    if (target) detail = detail ? `${detail} → ${target}` : target;
    const tagSuffix = betTag ? ` · ${betTag}` : '';
    const actionLabel = justLooked
        ? `${t('pages.zhaJinhua.looked')} · ${action}${tagSuffix}`
        : `${action}${tagSuffix}`;
    const meta = parseActionMeta(action);
    const kind = justLooked && !action.includes('看牌') ? 'look' : meta.kind;
    playerLastAction.value = {
        ...playerLastAction.value,
        [playerId]: {
            kind,
            icon: justLooked ? View : meta.icon,
            action: actionLabel,
            detail: detail || undefined,
        },
    };
};

type TurnSnapshot = {
    player_id: string;
    pot: number;
    phase?: string;
    pot_ledger?: PotEntry[];
    current_player_id?: string | null;
    balance?: number;
};

/** 作废进行中的 status 请求（开局/下一局/重置前调用） */
const invalidatePendingStatus = () => {
    statusFetchSeq += 1;
};

const ledgerMaxStep = (ledger: PotEntry[] | undefined): number => {
    if (!ledger?.length) return 0;
    return ledger.reduce((max, entry) => (entry.step > max ? entry.step : max), 0);
};

/** 拒绝 ledger 回退（同局 step 变小） */
const isLedgerRegression = (
    incoming: PotEntry[],
    current: PotEntry[],
    incomingRound: number,
    currentRound: number,
): boolean => {
    if (!current.length || !incoming.length) return false;
    if (incomingRound < currentRound) return true;
    if (incomingRound > currentRound) return false;
    return ledgerMaxStep(incoming) < ledgerMaxStep(current);
};

const pickLedger = (
    incoming: PotEntry[] | undefined,
    current: PotEntry[] | undefined,
    incomingRound: number,
    currentRound: number,
): PotEntry[] => {
    const inc = incoming ?? [];
    const cur = current ?? [];
    if (isLedgerRegression(inc, cur, incomingRound, currentRound)) {
        return [...cur];
    }
    if (inc.length) return [...inc];
    if (cur.length) return [...cur];
    return [];
};

const applyStatusSnapshot = (data: Status) => {
    const prev = status.value;
    if (!prev) {
        status.value = data;
        return;
    }
    status.value = {
        ...data,
        pot_ledger: pickLedger(data.pot_ledger, prev.pot_ledger, data.round, prev.round),
    };
};

/** turn 返回：以本手 ledger 为准立即同步（含下一位发话者） */
const patchTurnActResult = (data: TurnSnapshot) => {
    if (!status.value || !Array.isArray(data.pot_ledger)) return;
    const cur = status.value;
    const pid = data.player_id;
    const prevPlayer = cur.players[pid];
    status.value = {
        ...cur,
        pot: data.pot,
        phase: data.phase || cur.phase,
        current_player_id: data.current_player_id ?? cur.current_player_id,
        pot_ledger: [...data.pot_ledger],
        players: prevPlayer
            ? {
                ...cur.players,
                [pid]: { ...prevPlayer, balance: data.balance ?? prevPlayer.balance },
            }
            : cur.players,
    };
};

const applyNextPlayer = (nextPlayerId: string | null | undefined) => {
    if (!status.value || nextPlayerId === undefined) return;
    status.value = {
        ...status.value,
        current_player_id: nextPlayerId,
    };
};

const refreshStatus = async (): Promise<Status | null> => {
    const reqSeq = ++statusFetchSeq;
    const res = await getZhaJinhuaStatus();
    if (reqSeq !== statusFetchSeq) return null;
    applyStatusSnapshot(res.data);
    return status.value;
};

const showError = (err: unknown) => {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(typeof msg === 'string' ? msg : t('pages.zhaJinhua.error'));
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const clearRoundUi = () => {
    playerThoughtHistory.value = emptyThoughtHistory();
    playerLastAction.value = emptyPlayerActions();
    thinkingPlayer.value = null;
    refereeText.value = '';
};

const handleStart = async () => {
    loading.value = true;
    try {
        clearRoundUi();
        systemMessages.value = [];
        invalidatePendingStatus();
        const res = await startZhaJinhuaGame();
        systemMessages.value.push(res.data.message);
        await refreshStatus();
        if (res.data.pot_ledger?.length && status.value) {
            status.value = {
                ...status.value,
                pot: res.data.pot ?? status.value.pot,
                pot_ledger: [...res.data.pot_ledger],
            };
        }
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
        invalidatePendingStatus();
        const res = await nextZhaJinhuaRound();
        systemMessages.value.push(res.data.message);
        await refreshStatus();
        if (res.data.pot_ledger?.length && status.value) {
            status.value = {
                ...status.value,
                pot: res.data.pot ?? status.value.pot,
                pot_ledger: [...res.data.pot_ledger],
            };
        }
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
        invalidatePendingStatus();
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
    const wasLooked = status.value?.players[playerId]?.has_looked ?? false;
    thinkingPlayer.value = playerId;
    await sleep(350);

    try {
        const res = await zhaJinhuaTurn(playerId);
        const data = res.data;
        const nextPlayerId = data.current_player_id ?? null;

        if (data.skipped) {
            systemMessages.value.push(`【${data.display_name}】${data.reason || t('pages.zhaJinhua.skipped')}`);
            patchTurnActResult(data);
            await refreshStatus();
            applyNextPlayer(nextPlayerId);
            return data;
        }

        appendThought(playerId, data.thought || '……', data.action);
        patchTurnActResult(data);
        await refreshStatus();
        applyNextPlayer(nextPlayerId);

        const justLooked = !wasLooked && (status.value?.players[playerId]?.has_looked ?? false);
        setPlayerAction(
            playerId,
            data.action,
            data.amount ?? 0,
            data.target || undefined,
            justLooked,
            data.bet_tag || undefined,
        );

        await nextTick();
        await sleep(TURN_LEDGER_PAUSE_MS);
        // 以 turn 响应的下一位为准，避免 refresh 未完成时仍停在刚行动玩家
        applyNextPlayer(nextPlayerId);
        return data;
    } catch (err) {
        showError(err);
        await refreshStatus().catch(() => undefined);
        throw err;
    } finally {
        thinkingPlayer.value = null;
    }
};

const handleAutoRound = async () => {
    if (!canSimulate.value) return;
    simulating.value = true;
    try {
        await refreshStatus();
        let guard = 0;
        let hadAction = false;
        while (status.value?.phase === 'betting' && guard < MAX_AUTO_TURNS_ABS) {
            guard += 1;
            const current = status.value?.current_player_id;
            if (!current) break;
            const data = await runOneTurn(current);
            if (!data.skipped) hadAction = true;
        }

        if (status.value?.phase === 'betting') {
            systemMessages.value.push(t('pages.zhaJinhua.autoStuckHint'));
        }

        if (hadAction) {
            thinkingPlayer.value = '__referee__';
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
    align-items: start;
}

@media (max-width: 900px) {
    .players-row {
        grid-template-columns: 1fr;
    }
}

.player-slot {
    position: relative;
    min-width: 0;
}

.player-slot--betting {
    padding-top: 44px;
}

.turn-mic-float {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    padding: 8px 16px;
    border-radius: 999px;
    font-size: 15px;
    font-weight: 700;
    color: #d35400;
    background: linear-gradient(90deg, #fff3cd, #ffeaa7);
    border: 2px solid #f39c12;
    box-shadow: 0 4px 14px rgba(243, 156, 18, 0.35);
    animation: turn-glow 1.5s ease-in-out infinite;
    white-space: nowrap;
    z-index: 3;
    pointer-events: none;
}

.player-panel {
    position: relative;
    padding: 16px;
    padding-top: 36px;
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

.thinking-badge {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 6px 10px;
    border-radius: 10px 10px 0 0;
    font-size: 13px;
    font-weight: 600;
    color: #b7791f;
    background: linear-gradient(90deg, #fff8e6, #ffedd5);
}

.status-badge {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    text-align: center;
    padding: 6px 10px;
    border-radius: 10px 10px 0 0;
    font-size: 12px;
    font-weight: 500;
    color: var(--el-text-color-secondary);
    background: var(--el-fill-color-light);
}

@keyframes turn-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(243, 156, 18, 0.3); }
    50% { box-shadow: 0 0 12px 2px rgba(243, 156, 18, 0.45); }
}

/* ── 玩家右上角行动角标 ── */
.player-action-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 2;
    display: inline-flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
    max-width: calc(100% - 16px);
    padding: 6px 10px;
    border-radius: 10px;
    border: 2px solid var(--el-border-color);
    background: var(--el-fill-color-blank);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    animation: action-badge-in 0.3s ease-out;
}

@keyframes action-badge-in {
    from {
        opacity: 0;
        transform: scale(0.85) translateY(-4px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}

.action-badge-icon {
    font-size: 18px;
}

.action-badge-verb {
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 1px;
    white-space: nowrap;
}

.action-badge-detail {
    font-size: 11px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
    white-space: nowrap;
}

.player-action-badge.action-call { border-color: #3498db; background: linear-gradient(180deg, #ebf5fb 0%, #fff 100%); }
.player-action-badge.action-call .action-badge-icon,
.player-action-badge.action-call .action-badge-verb { color: #2980b9; }

.player-action-badge.action-raise { border-color: #e74c3c; background: linear-gradient(180deg, #fdedec 0%, #fff 100%); }
.player-action-badge.action-raise .action-badge-icon,
.player-action-badge.action-raise .action-badge-verb { color: #c0392b; }

.player-action-badge.action-look { border-color: #9b59b6; background: linear-gradient(180deg, #f5eef8 0%, #fff 100%); }
.player-action-badge.action-look .action-badge-icon,
.player-action-badge.action-look .action-badge-verb { color: #8e44ad; }

.player-action-badge.action-compare { border-color: #e67e22; background: linear-gradient(180deg, #fef5e7 0%, #fff 100%); }
.player-action-badge.action-compare .action-badge-icon,
.player-action-badge.action-compare .action-badge-verb { color: #d35400; }

.player-action-badge.action-fold { border-color: #95a5a6; background: linear-gradient(180deg, #f4f6f7 0%, #fff 100%); }
.player-action-badge.action-fold .action-badge-icon,
.player-action-badge.action-fold .action-badge-verb { color: #7f8c8d; }

.player-action-badge.action-default { border-color: var(--el-border-color); }
.player-action-badge.action-default .action-badge-verb { color: var(--el-text-color-primary); }

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

.settlement-pot-total {
    margin-left: 12px;
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
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
