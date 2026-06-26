export interface AgentStep {
    agent: string;
    role: string;
    input: string;
    output: string;
    status: 'pending' | 'running' | 'done' | 'error';
    meta?: string;
}

export interface AgentExample {
    label: string;
    question: string;
    tip: string;
}
