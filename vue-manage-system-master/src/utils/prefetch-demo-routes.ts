/** 功能展示下除人脸打卡外的演示页，空闲时预拉 chunk，避免 dev 首次点击等待编译 */
const DEMO_ROUTE_LOADERS = [
    () => import('@/views/demo/complaints.vue'),
    () => import('@/views/demo/rag.vue'),
    () => import('@/views/demo/ai-chat.vue'),
    () => import('@/views/demo/agent.vue'),
    () => import('@/views/demo/meeting.vue'),
    () => import('@/views/demo/smart-route.vue'),
    () => import('@/views/demo/cobol-migrate.vue'),
] as const;

let prefetched = false;

function runPrefetch() {
    for (const load of DEMO_ROUTE_LOADERS) {
        load().catch(() => {
            /* 预拉失败不影响正常导航 */
        });
    }
}

export function prefetchDemoRoutes() {
    if (prefetched) return;
    prefetched = true;

    if (typeof requestIdleCallback !== 'undefined') {
        requestIdleCallback(runPrefetch, { timeout: 3000 });
    } else {
        setTimeout(runPrefetch, 500);
    }
}
