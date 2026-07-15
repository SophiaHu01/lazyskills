// 帧 OCR 小工具(macOS Vision 框架,零外部依赖) — 视觉轨的地基
// 编译: swiftc -O ocr.swift -o ocr    用法: ./ocr <图片路径>  → 每行一条识别文本
import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    FileHandle.standardError.write("用法: ocr <image>\n".data(using: .utf8)!)
    exit(1)
}
let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("读图失败: \(path)\n".data(using: .utf8)!)
    exit(1)
}
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.recognitionLanguages = ["zh-Hans", "en-US"]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try handler.perform([req])
// --boxes: 每行输出 归一化x,y,w,h\t文本(y 从顶部起算),供内容黑名单定位与自动裁剪
let boxes = CommandLine.arguments.contains("--boxes")
for obs in req.results ?? [] {
    if let top = obs.topCandidates(1).first {
        if boxes {
            let b = obs.boundingBox   // Vision 坐标系:原点左下
            let y = 1 - b.origin.y - b.height
            print(String(format: "%.3f,%.3f,%.3f,%.3f\t%@", b.origin.x, y, b.width, b.height, top.string))
        } else {
            print(top.string)
        }
    }
}
