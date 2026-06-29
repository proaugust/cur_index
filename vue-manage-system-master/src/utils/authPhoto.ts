import request from './request';

const cache = new Map<string, string>();
const pending = new Map<string, Promise<string>>();

function cacheKey(userId: string, version: number) {
    return `${userId}@${version}`;
}

export function revokeAttendancePersonPhoto(userId?: string) {
    for (const [key, url] of cache.entries()) {
        if (!userId || key.startsWith(`${userId}@`)) {
            URL.revokeObjectURL(url);
            cache.delete(key);
        }
    }
}

/** 带 JWT 拉取人员标准照，返回可给 <img> 使用的 blob URL */
export async function loadAttendancePersonPhoto(userId: string, version = 0): Promise<string> {
    const key = cacheKey(userId, version);
    const hit = cache.get(key);
    if (hit) return hit;

    let task = pending.get(key);
    if (!task) {
        task = request
            .get(`/attendance/persons/${encodeURIComponent(userId)}/photo`, {
                params: { v: version, _t: Date.now() },
                responseType: 'blob',
                headers: { 'Cache-Control': 'no-cache' },
            })
            .then((res) => {
                const url = URL.createObjectURL(res.data as Blob);
                cache.set(key, url);
                pending.delete(key);
                return url;
            })
            .catch((err) => {
                pending.delete(key);
                throw err;
            });
        pending.set(key, task);
    }
    return task;
}
