// 事件系统类型:events=[{type,start,hold,props}](秒)。
// 每个组件 = {event} 进、AbsoluteFill 出,透明背景,spring 进场 + 淡出。

export type ChapterCardProps = {
  no: number | string;
  title: string;
  sub?: string;
};

export type BigNumberProps = {
  value: number;
  unit?: string;
  label?: string;
};

export type QuickChartItem = {
  label: string;
  value: number;
  highlight?: boolean;
};

export type QuickChartProps = {
  kind: 'bar';
  items: QuickChartItem[];
  unit?: string;
};

export type StepsTimelineProps = {
  steps: string[];
  active?: number;
};

export type CalloutProps = {
  shape: 'arrow' | 'circle' | 'underline';
  // 归一化坐标(0-1),相对 1080x1920 画布
  x: number;
  y: number;
  w?: number;
  h?: number;
  label?: string;
};

export type ListRevealProps = {
  title: string;
  items: string[];
};

export type QuoteCardProps = {
  text: string;
  by?: string;
};

type EventBase = {
  start: number; // 秒
  hold: number; // 秒(不含出场淡出)
};

export type MotionEvent =
  | (EventBase & {type: 'ChapterCard'; props: ChapterCardProps})
  | (EventBase & {type: 'BigNumber'; props: BigNumberProps})
  | (EventBase & {type: 'QuickChart'; props: QuickChartProps})
  | (EventBase & {type: 'StepsTimeline'; props: StepsTimelineProps})
  | (EventBase & {type: 'Callout'; props: CalloutProps})
  | (EventBase & {type: 'ListReveal'; props: ListRevealProps})
  | (EventBase & {type: 'QuoteCard'; props: QuoteCardProps});

export type VidMotionProps = {
  events: MotionEvent[];
  durationSec: number;
  width?: number;   // 画布尺寸跟素材,默认竖屏
  height?: number;
};
