import AppKit
import Foundation

struct Cue {
    let start: Double
    let end: Double
    let text: String
}

struct Segment {
    let start: Double
    let end: Double
    let zh: String
    let en: String
}

func parseTime(_ raw: String) -> Double {
    let cleaned = raw.trimmingCharacters(in: .whitespacesAndNewlines)
    let pieces = cleaned.split(separator: ":")
    guard pieces.count == 3 else { return 0 }
    let secondsParts = pieces[2].split(separator: ",")
    let hours = Double(pieces[0]) ?? 0
    let minutes = Double(pieces[1]) ?? 0
    let seconds = Double(secondsParts.first ?? "0") ?? 0
    let millis = Double(secondsParts.dropFirst().first ?? "0") ?? 0
    return hours * 3600 + minutes * 60 + seconds + millis / 1000
}

func parseSRT(path: String) throws -> [Cue] {
    let content = try String(contentsOfFile: path, encoding: .utf8)
        .replacingOccurrences(of: "\r\n", with: "\n")
        .replacingOccurrences(of: "\r", with: "\n")
    return content.components(separatedBy: "\n\n").compactMap { block in
        let lines = block.split(separator: "\n", omittingEmptySubsequences: false).map(String.init)
        guard let timingIndex = lines.firstIndex(where: { $0.contains("-->") }) else { return nil }
        let timing = lines[timingIndex].components(separatedBy: "-->")
        guard timing.count == 2 else { return nil }
        let text = lines.dropFirst(timingIndex + 1)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
            .joined(separator: " ")
        guard !text.isEmpty else { return nil }
        return Cue(start: parseTime(timing[0]), end: parseTime(timing[1]), text: text)
    }
}

func activeText(_ cues: [Cue], at time: Double) -> String {
    cues.first { $0.start <= time && time < $0.end }?.text ?? ""
}

func makeFont(_ names: [String], size: CGFloat, weight: NSFont.Weight) -> NSFont {
    for name in names {
        if let font = NSFont(name: name, size: size) {
            return font
        }
    }
    return NSFont.systemFont(ofSize: size, weight: weight)
}

func measuredHeight(_ text: String, width: CGFloat, font: NSFont, lineBreakMode: NSLineBreakMode) -> CGFloat {
    guard !text.isEmpty else { return 0 }
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = .center
    paragraph.lineBreakMode = lineBreakMode
    paragraph.maximumLineHeight = font.pointSize * 1.16
    paragraph.minimumLineHeight = font.pointSize * 1.16
    let rect = NSString(string: text).boundingRect(
        with: CGSize(width: width, height: 1000),
        options: [.usesLineFragmentOrigin, .usesFontLeading],
        attributes: [.font: font, .paragraphStyle: paragraph]
    )
    return ceil(rect.height) + 12
}

func drawOutlinedText(_ text: String, in rect: CGRect, font: NSFont, fill: NSColor, outline: CGFloat, lineBreakMode: NSLineBreakMode) {
    guard !text.isEmpty else { return }
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = .center
    paragraph.lineBreakMode = lineBreakMode
    paragraph.maximumLineHeight = font.pointSize * 1.16
    paragraph.minimumLineHeight = font.pointSize * 1.16
    let baseAttrs: [NSAttributedString.Key: Any] = [.font: font, .paragraphStyle: paragraph, .kern: 0]
    let outlineAttrs = baseAttrs.merging([.foregroundColor: NSColor.black]) { _, new in new }
    let fillAttrs = baseAttrs.merging([.foregroundColor: fill]) { _, new in new }
    let string = NSString(string: text)
    let radius = Int(ceil(outline))
    for dx in -radius...radius {
        for dy in -radius...radius {
            if dx == 0 && dy == 0 { continue }
            if hypot(Double(dx), Double(dy)) <= Double(outline) + 0.35 {
                string.draw(in: rect.offsetBy(dx: CGFloat(dx), dy: CGFloat(dy)), withAttributes: outlineAttrs)
            }
        }
    }
    string.draw(in: rect, withAttributes: fillAttrs)
}

func textWidth(_ text: String, font: NSFont) -> CGFloat {
    NSString(string: text).size(withAttributes: [.font: font]).width
}

func wrapByCharacters(_ text: String, font: NSFont, maxWidth: CGFloat) -> String {
    var lines: [String] = []
    var current = ""
    for char in text {
        let candidate = current + String(char)
        if !current.isEmpty && textWidth(candidate, font: font) > maxWidth {
            lines.append(current)
            current = String(char)
        } else {
            current = candidate
        }
    }
    if !current.isEmpty {
        lines.append(current)
    }
    return lines.joined(separator: "\n")
}

func wrapByWords(_ text: String, font: NSFont, maxWidth: CGFloat) -> String {
    let words = text.split(separator: " ").map(String.init)
    guard !words.isEmpty else { return text }
    var lines: [String] = []
    var current = ""
    for word in words {
        let candidate = current.isEmpty ? word : current + " " + word
        if !current.isEmpty && textWidth(candidate, font: font) > maxWidth {
            lines.append(current)
            current = word
        } else {
            current = candidate
        }
    }
    if !current.isEmpty {
        lines.append(current)
    }
    return lines.joined(separator: "\n")
}

func render(segment: Segment, index: Int, outDir: URL, width: Int, height: Int) throws -> String {
    let scale = CGFloat(height) / 1080
    let image = NSImage(size: NSSize(width: width, height: height))
    image.lockFocus()
    NSColor.clear.setFill()
    NSRect(x: 0, y: 0, width: width, height: height).fill()
    NSGraphicsContext.current?.imageInterpolation = .high
    NSGraphicsContext.current?.shouldAntialias = true

    let zhFont = makeFont(["PingFangSC-Semibold", "PingFang SC Semibold", "PingFang SC"], size: 46 * scale, weight: .semibold)
    let enFont = makeFont(["Arial Black", "Arial-Black", "Arial Bold"], size: 34 * scale, weight: .black)
    let textBoxWidth = CGFloat(width) * 0.84
    let left = (CGFloat(width) - textBoxWidth) / 2
    let zhText = wrapByCharacters(segment.zh, font: zhFont, maxWidth: textBoxWidth)
    let enText = wrapByWords(segment.en, font: enFont, maxWidth: textBoxWidth)
    let enHeight = measuredHeight(enText, width: textBoxWidth, font: enFont, lineBreakMode: .byWordWrapping)
    let zhHeight = measuredHeight(zhText, width: textBoxWidth, font: zhFont, lineBreakMode: .byCharWrapping)
    let enY: CGFloat = 52 * scale
    let zhY = enY + enHeight + 8 * scale

    drawOutlinedText(zhText, in: CGRect(x: left, y: zhY, width: textBoxWidth, height: zhHeight), font: zhFont, fill: NSColor(calibratedRed: 1, green: 0.90, blue: 0, alpha: 1), outline: 5 * scale, lineBreakMode: .byCharWrapping)
    drawOutlinedText(enText, in: CGRect(x: left, y: enY, width: textBoxWidth, height: enHeight), font: enFont, fill: NSColor.white, outline: 4 * scale, lineBreakMode: .byWordWrapping)
    image.unlockFocus()

    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let png = bitmap.representation(using: .png, properties: [:]) else {
        throw NSError(domain: "render", code: 2, userInfo: [NSLocalizedDescriptionKey: "PNG encoding failed"])
    }
    let filename = String(format: "subtitle_%05d.png", index)
    let url = outDir.appendingPathComponent(filename)
    try png.write(to: url)
    return url.path
}

let args = CommandLine.arguments
guard args.count >= 8 else {
    FileHandle.standardError.write(Data("Usage: render_bilingual_overlay.swift zh.srt en.srt out_dir duration_seconds concat.txt width height\n".utf8))
    exit(2)
}

let zhPath = args[1]
let enPath = args[2]
let outDir = URL(fileURLWithPath: args[3])
let duration = Double(args[4]) ?? 0
let concatPath = args[5]
let width = Int(args[6]) ?? 1920
let height = Int(args[7]) ?? 1080

try FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let zhCues = try parseSRT(path: zhPath)
let enCues = try parseSRT(path: enPath)

var boundaries = Set<Double>([0, duration])
for cue in zhCues + enCues {
    if cue.start < duration && cue.end > 0 {
        boundaries.insert(max(0, cue.start))
        boundaries.insert(min(duration, cue.end))
    }
}

let sorted = boundaries.sorted()
var segments: [Segment] = []
for pair in zip(sorted.dropLast(), sorted.dropFirst()) {
    let start = pair.0
    let end = pair.1
    guard end - start > 0.01 else { continue }
    let midpoint = (start + end) / 2
    let segment = Segment(start: start, end: end, zh: activeText(zhCues, at: midpoint), en: activeText(enCues, at: midpoint))
    if let last = segments.last, last.zh == segment.zh, last.en == segment.en, abs(last.end - segment.start) < 0.001 {
        segments[segments.count - 1] = Segment(start: last.start, end: segment.end, zh: last.zh, en: last.en)
    } else {
        segments.append(segment)
    }
}

var concat = ""
for (index, segment) in segments.enumerated() {
    let imagePath = try render(segment: segment, index: index, outDir: outDir, width: width, height: height)
    concat += "file '\(imagePath.replacingOccurrences(of: "'", with: "'\\''"))'\n"
    concat += String(format: "duration %.3f\n", locale: Locale(identifier: "en_US_POSIX"), segment.end - segment.start)
}
if !segments.isEmpty {
    let imagePath = outDir.appendingPathComponent(String(format: "subtitle_%05d.png", segments.count - 1)).path
    concat += "file '\(imagePath.replacingOccurrences(of: "'", with: "'\\''"))'\n"
}
try concat.write(toFile: concatPath, atomically: true, encoding: .utf8)
print("Rendered \(segments.count) subtitle segments")
