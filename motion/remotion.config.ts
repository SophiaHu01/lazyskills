import {Config} from '@remotion/cli/config';

// 透明层导出默认值(命令行 flag 会覆盖,这里只是兜底)
Config.setVideoImageFormat('png');
Config.setOverwriteOutput(true);
