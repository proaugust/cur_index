export const setProperty = (prop: string, val: any, dom = document.documentElement) => {
    dom.style.setProperty(prop, val);
};

/** ISO / 后端时间 → YYYY-MM-DD HH:mm:ss */
export const formatDateTime = (value?: string | null): string => {
    if (value == null || value === '') return '-';
    const raw = String(value).trim();
    const m = raw.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/);
    return m ? `${m[1]} ${m[2]}` : raw;
};

export const mix = (color1: string, color2: string, weight: number = 0.5): string => {
    let color = '#';
    for (let i = 0; i <= 2; i++) {
        const c1 = parseInt(color1.substring(1 + i * 2, 3 + i * 2), 16);
        const c2 = parseInt(color2.substring(1 + i * 2, 3 + i * 2), 16);
        const c = Math.round(c1 * weight + c2 * (1 - weight));
        color += c.toString(16).padStart(2, '0');
    }
    return color;
};
