<template>
    <div class="pot-table-wrap" :class="wrapClass">
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
                <tr v-for="row in rows" :key="`${rowKeyPrefix}-${row.step}`">
                    <td class="col-step">{{ row.step }}</td>
                    <td class="col-player" :style="{ color: playerColor(row.player_id) }">
                        {{ row.display_name }}
                    </td>
                    <td class="col-action">
                        <span class="pot-action-tag" :class="'pot-action--' + row.action_kind">
                            {{ actionLabel(row.action_kind) }}
                        </span>
                        <span
                            v-if="betTagLabel(row.bet_kind)"
                            class="pot-action-tag pot-action-tag--bet"
                            :class="row.bet_kind ? 'pot-bet--' + row.bet_kind : 'pot-bet--unknown'"
                        >
                            {{ betTagLabel(row.bet_kind) }}
                        </span>
                        <span v-if="row.all_in" class="pot-action-tag pot-bet--allin">
                            {{ t('pages.zhaJinhua.allIn') }}
                        </span>
                    </td>
                    <td class="col-amt">
                        <template v-if="row.display_amount != null && row.display_amount > 0">
                            +{{ row.display_amount }}
                        </template>
                        <span v-else class="col-amt-zero">—</span>
                    </td>
                    <td class="col-running">{{ row.pool_running }} {{ t('pages.zhaJinhua.yuan') }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script setup lang="ts" name="zha-jinhua-pot-ledger-table">
import { useI18n } from 'vue-i18n';

/** 与后端 ZhaJinhuaPotLedgerRow 一致，前端只渲染 */
export type PotLedgerRow = {
    step: number;
    player_id: string;
    display_name: string;
    amount: number;
    display_amount: number | null;
    reason: string;
    line_stake: number;
    pool_running: number;
    player_running: number;
    action_kind: string;
    bet_kind: string;
    all_in: boolean;
    at_line: boolean;
};

defineProps<{
    rows: PotLedgerRow[];
    rowKeyPrefix: string;
    playerColor: (playerId: string) => string;
    wrapClass?: string;
}>();

const { t } = useI18n();

const actionLabel = (kind: string): string => {
    const map: Record<string, string> = {
        ante: t('pages.zhaJinhua.ante'),
        call: t('pages.zhaJinhua.call'),
        raise: t('pages.zhaJinhua.raise'),
        compare: t('pages.zhaJinhua.compare'),
        fold: t('pages.zhaJinhua.fold'),
        showdown: t('pages.zhaJinhua.showdown'),
    };
    return map[kind] ?? kind;
};

const betTagLabel = (betKind: string): string => {
    if (betKind === 'open') return t('pages.zhaJinhua.betOpen');
    if (betKind === 'blind') return t('pages.zhaJinhua.betBlind');
    return '';
};
</script>

<style scoped>
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

.col-amt-zero {
    color: var(--el-text-color-placeholder);
    font-weight: 400;
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

.pot-action-tag--bet {
    margin-left: 4px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

.pot-bet--blind {
    background: #3d4f5f;
    color: #ecf0f1;
    border: 1px solid #2c3e50;
}

.pot-bet--open {
    background: linear-gradient(180deg, #fde68a 0%, #fbbf24 100%);
    color: #78350f;
    border: 1px solid #d97706;
}

.pot-bet--allin {
    margin-left: 4px;
    background: #fef3c7;
    color: #c05621;
    border: 1px solid #ed8936;
    font-weight: 700;
}

.pot-bet--unknown {
    background: #edf2f7;
    color: #4a5568;
    border: 1px solid #cbd5e0;
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

.pot-action--fold {
    background: #eaecee;
    color: #566573;
}

.pot-action--showdown {
    background: #fdebd0;
    color: #b7950b;
    font-weight: 800;
}

.pot-action--default {
    background: #f4f6f7;
    color: #566573;
}
</style>
