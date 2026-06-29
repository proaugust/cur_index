export interface Menus {
    id: string;
    pid?: string;
    icon?: string;
    index: string;
    titleKey: string;
    permiss?: string;
    children?: Menus[];
}