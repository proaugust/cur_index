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
                        <span class="pot-action-tag" :class="'pot-action--' + row.actionKind">
                            {{ row.actionLabel }}
                        </span>
                        <span
                            v-if="row.tagLabel"
                            class="pot-action-tag pot-action-tag--bet"
                            :class="row.betKind ? 'pot-bet--' + row.betKind : 'pot-bet--unknown'"
                        >
                            {{ row.tagLabel }}
                        </span>
                        <span v-if="row.extraTag" class="pot-action-tag pot-bet--allin">
                            {{ row.extraTag }}
                        </span>
                    </td>
                    <td class="col-amt">
                        <template v-if="betLineStake(row) !== null">+{{ betLineStake(row) }}</template>
                        <span v-else class="col-amt-zero">—</span>
                    </td>
                    <td class="col-running">{{ row.running }} {{ t('pages.zhaJinhua.yuan') }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script setup lang="ts" name="zha-jinhua-pot-ledger-table">
import { useI18n } from 'vue-i18n';

export type PotLedgerRow = {
    step: number;
    player_id: string;
    display_name: string;
    amount: number;
    line_stake?: number;
    actionLabel: string;
    actionKind: string;
    tagLabel: string;
    betKind: '' | 'blind' | 'open';
    extraTag: string;
    running: number;
    atLine: boolean;
};

defineProps<{
    rows: PotLedgerRow[];
    rowKeyPrefix: string;
    playerColor: (playerId: string) => string;
    wrapClass?: string;
}>();

const { t } = useI18n();

const betLineStake = (row: PotLedgerRow): number | null => {
    const stake = row.line_stake ?? 0;
    if (stake > 0 && (row.actionKind === 'call' || row.actionKind === 'raise' || row.actionKind === 'compare')) {
        return stake;
    }
    if (row.amount > 0) return row.amount;
    return null;
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

.col-amt-atline {
    color: var(--el-color-success);
    font-weight: 800;
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
