import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {BigNumber} from './components/BigNumber';
import {Callout} from './components/Callout';
import {ChapterCard} from './components/ChapterCard';
import {ListReveal} from './components/ListReveal';
import {QuickChart} from './components/QuickChart';
import {QuoteCard} from './components/QuoteCard';
import {StepsTimeline} from './components/StepsTimeline';
import {EXIT_WINDOW_F} from './components/timing';
import type {MotionEvent, VidMotionProps} from './types';

// 动效透明层:events=[{type,start,hold,props}](秒)。
// 密度红线(motion-rules.md):同屏只渲一个——按 start 排序取最近的活跃项。

function renderEvent(ev: MotionEvent): React.ReactNode {
  switch (ev.type) {
    case 'ChapterCard':
      return <ChapterCard event={ev} />;
    case 'BigNumber':
      return <BigNumber event={ev} />;
    case 'QuickChart':
      return <QuickChart event={ev} />;
    case 'StepsTimeline':
      return <StepsTimeline event={ev} />;
    case 'Callout':
      return <Callout event={ev} />;
    case 'ListReveal':
      return <ListReveal event={ev} />;
    case 'QuoteCard':
      return <QuoteCard event={ev} />;
    default:
      return null;
  }
}

export const VidMotion: React.FC<VidMotionProps> = ({events}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const active = [...events]
    .sort((a, b) => a.start - b.start)
    .filter((e) => t >= e.start && t <= e.start + e.hold + EXIT_WINDOW_F / fps);
  // 同屏只渲一个:重叠时后开始的赢(前一个立即让位)
  const current = active.length > 0 ? active[active.length - 1] : null;
  return <AbsoluteFill>{current ? renderEvent(current) : null}</AbsoluteFill>;
};
