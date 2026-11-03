// Kiln site — device imagery composer (dev-only, run on a Mac).
//
// Renders localized app screenshots inside Apple's product bezels (Design
// Resources kits) on a BAKED background colour and writes JPEGs, so the site
// ships small opaque images instead of multi-megabyte transparent PNGs. The
// screen opening of each bezel is measured from its alpha channel (same method
// as Kiln's scripts/screenshots/frame-bezel.swift), so any kit works.
//
// Usage:
//   site_images phone <shot.png> <bezel.png> <out.jpg> <outWidth> <#bg>
//   site_images mac   <window.png> <bezel.png> <out.jpg> <outWidth> <#bg>
//   site_images hero  <window.png> <macBezel.png> <phoneShot.png> <phoneBezel.png> <out.jpg> <outW> <outH> <#bg>
import AppKit
import ImageIO

// ── Bezel geometry ─────────────────────────────────────────────────────────
struct Bezel {
    let image: NSImage
    let size: CGSize          // pixels
    let hole: CGRect          // opening, top-down pixel coordinates
    let radius: CGFloat       // opening corner radius (top-left), pixels

    init(path: String) {
        guard let img = NSImage(contentsOfFile: path),
              let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil)
        else { fputs("can't load bezel \(path)\n", stderr); exit(1) }
        image = img
        let bw = cg.width, bh = cg.height
        let ctx = CGContext(data: nil, width: bw, height: bh, bitsPerComponent: 8, bytesPerRow: bw*4,
                            space: CGColorSpaceCreateDeviceRGB(),
                            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        ctx.draw(cg, in: CGRect(x: 0, y: 0, width: bw, height: bh))
        let px = ctx.data!.bindMemory(to: UInt8.self, capacity: bw*bh*4)
        func alpha(_ x: Int, _ y: Int) -> UInt8 { px[(y*bw + x)*4 + 3] }   // row 0 = top
        let cx = bw/2, cy = bh/2
        // Union of several scan lines: one centre line stops early at a camera
        // cutout, Dynamic Island or notch, which all sit inside the opening.
        var hl = cx, hr = cx, ht = cy, hb = cy
        for fy in [0.25, 0.5, 0.75] {
            let y = Int(Double(bh) * fy)
            var l = cx; while l > 0 && alpha(l-1, y) == 0 { l -= 1 }
            var r = cx; while r < bw-1 && alpha(r+1, y) == 0 { r += 1 }
            hl = min(hl, l); hr = max(hr, r)
        }
        for fx in [0.2, 0.35, 0.5, 0.65, 0.8] {
            let x = Int(Double(bw) * fx)
            var t = cy; while t > 0 && alpha(x, t-1) == 0 { t -= 1 }
            var b = cy; while b < bh-1 && alpha(x, b+1) == 0 { b += 1 }
            ht = min(ht, t); hb = max(hb, b)
        }
        var r = 0
        for dy in 1..<min(600, (hb-ht)/2) {
            var x = hl - 1
            while x > 0 && x < bw-1 && alpha(x, ht + dy) == 0 { x += 1 }
            while x > 0 && x < bw-1 && alpha(x, ht + dy) != 0 { x += 1 }
            if x - hl <= 3 { r = dy; break }
        }
        size = CGSize(width: bw, height: bh)
        hole = CGRect(x: hl, y: ht, width: hr-hl+1, height: hb-ht+1)
        radius = CGFloat(r)
    }
}

func load(_ path: String) -> NSImage {
    guard let i = NSImage(contentsOfFile: path) else { fputs("can't load \(path)\n", stderr); exit(1) }
    return i
}

func color(_ hex: String) -> NSColor {
    var s = hex; if s.hasPrefix("#") { s.removeFirst() }
    let v = UInt32(s, radix: 16) ?? 0
    return NSColor(srgbRed: CGFloat((v >> 16) & 0xff)/255, green: CGFloat((v >> 8) & 0xff)/255,
                   blue: CGFloat(v & 0xff)/255, alpha: 1)
}

// ── Canvas ─────────────────────────────────────────────────────────────────
final class Canvas {
    let rep: NSBitmapImageRep
    let w: CGFloat, h: CGFloat
    init(_ w: Int, _ h: Int, bg: NSColor) {
        self.w = CGFloat(w); self.h = CGFloat(h)
        rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .calibratedRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        rep.size = NSSize(width: w, height: h)
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
        bg.setFill(); NSBezierPath(rect: NSRect(x: 0, y: 0, width: w, height: h)).fill()
    }
    var ctx: CGContext { NSGraphicsContext.current!.cgContext }

    /// Draws `bezel` scaled into `frame` (Cocoa coordinates, bottom-up) with a
    /// soft shadow cast by its own silhouette, then `content` through the
    /// opening, then the bezel again on top so rim and cutouts cover the edges.
    func device(_ bezel: Bezel, in frame: NSRect, shadow: CGFloat = 0.5,
                content: (NSRect) -> Void) {
        let s = frame.width / bezel.size.width
        let screen = NSRect(x: frame.minX + bezel.hole.minX * s,
                            y: frame.minY + (bezel.size.height - bezel.hole.maxY) * s,
                            width: bezel.hole.width * s, height: bezel.hole.height * s)
        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: -frame.width * 0.02), blur: frame.width * 0.08,
                      color: NSColor(white: 0, alpha: shadow).cgColor)
        bezel.image.draw(in: frame, from: .zero, operation: .sourceOver, fraction: 1)
        ctx.restoreGState()
        ctx.saveGState()
        NSBezierPath(roundedRect: screen, xRadius: bezel.radius * s, yRadius: bezel.radius * s).addClip()
        NSColor.black.setFill(); NSBezierPath(rect: screen).fill()
        content(screen)
        ctx.restoreGState()
        bezel.image.draw(in: frame, from: .zero, operation: .sourceOver, fraction: 1)
    }

    func writeJPEG(_ path: String, quality: CGFloat = 0.82) {
        NSGraphicsContext.restoreGraphicsState()
        guard let cg = rep.cgImage else { exit(1) }
        // Flatten onto opaque RGB: Safari and the App Store-style pipelines both
        // prefer no alpha, and JPEG has none anyway.
        let o = CGContext(data: nil, width: cg.width, height: cg.height, bitsPerComponent: 8, bytesPerRow: 0,
                          space: CGColorSpace(name: CGColorSpace.sRGB)!,
                          bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
        o.draw(cg, in: CGRect(x: 0, y: 0, width: cg.width, height: cg.height))
        let url = URL(fileURLWithPath: path)
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let dest = CGImageDestinationCreateWithURL(url as CFURL, "public.jpeg" as CFString, 1, nil)!
        CGImageDestinationAddImage(dest, o.makeImage()!, [kCGImageDestinationLossyCompressionQuality: quality] as CFDictionary)
        CGImageDestinationFinalize(dest)
        print("✓ \(path)  \(cg.width)×\(cg.height)")
    }
}

/// Fill the device screen with a phone capture (aspect-fit; captures match).
func fillScreen(_ shot: NSImage) -> (NSRect) -> Void {
    { screen in
        let f = min(screen.width / shot.size.width, screen.height / shot.size.height)
        let w = shot.size.width * f, h = shot.size.height * f
        shot.draw(in: NSRect(x: screen.midX - w/2, y: screen.midY - h/2, width: w, height: h),
                  from: .zero, operation: .sourceOver, fraction: 1)
    }
}

/// A Mac screen: dark ember wallpaper with the app window centred on it.
func macDesktop(_ window: NSImage, widthFraction: CGFloat = 0.9) -> (NSRect) -> Void {
    { screen in
        NSGradient(colors: [NSColor(srgbRed: 0.20, green: 0.09, blue: 0.06, alpha: 1),
                            NSColor(srgbRed: 0.07, green: 0.05, blue: 0.06, alpha: 1)])!
            .draw(in: screen, angle: -70)
        let glowC = CGPoint(x: screen.midX, y: screen.minY + screen.height * 0.85)
        let glow = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(),
            colors: [NSColor(srgbRed: 1, green: 0.42, blue: 0.2, alpha: 0.35).cgColor,
                     NSColor(srgbRed: 1, green: 0.42, blue: 0.2, alpha: 0).cgColor] as CFArray, locations: [0, 1])!
        NSGraphicsContext.current!.cgContext.drawRadialGradient(glow, startCenter: glowC, startRadius: 0,
            endCenter: glowC, endRadius: screen.width * 0.7, options: [])
        let w = screen.width * widthFraction, h = w * window.size.height / window.size.width
        let r = NSRect(x: screen.midX - w/2, y: screen.midY - h/2 - screen.height * 0.01, width: w, height: h)
        let ctx = NSGraphicsContext.current!.cgContext
        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: -w * 0.012), blur: w * 0.04,
                      color: NSColor(white: 0, alpha: 0.55).cgColor)
        NSColor.white.setFill()
        NSBezierPath(roundedRect: r, xRadius: w * 0.011, yRadius: w * 0.011).fill()
        ctx.restoreGState()
        ctx.saveGState()
        NSBezierPath(roundedRect: r, xRadius: w * 0.011, yRadius: w * 0.011).addClip()
        window.draw(in: r, from: .zero, operation: .sourceOver, fraction: 1)
        ctx.restoreGState()
    }
}

// ── Commands ───────────────────────────────────────────────────────────────
let a = CommandLine.arguments
guard a.count >= 2 else { fputs("usage: see header\n", stderr); exit(1) }
switch a[1] {
case "phone":
    let shot = load(a[2]), bezel = Bezel(path: a[3]), out = a[4]
    let outW = Int(a[5])!, bg = color(a[6])
    // Pad around the device so its shadow is not clipped by the image edge.
    let pad: CGFloat = 0.06
    let devW = CGFloat(outW) * (1 - 2*pad)
    let devH = devW * bezel.size.height / bezel.size.width
    let outH = Int(devH + CGFloat(outW) * 2 * pad)
    let c = Canvas(outW, outH, bg: bg)
    c.device(bezel, in: NSRect(x: CGFloat(outW)*pad, y: CGFloat(outW)*pad, width: devW, height: devH),
             content: fillScreen(shot))
    c.writeJPEG(out)
case "mac":
    let window = load(a[2]), bezel = Bezel(path: a[3]), out = a[4]
    let outW = Int(a[5])!, bg = color(a[6])
    // 4% side margin and room below the feet so the shadow isn't cut off.
    let devW = CGFloat(outW) * 0.92
    let devH = devW * bezel.size.height / bezel.size.width
    let c = Canvas(outW, Int(devH + CGFloat(outW) * 0.05), bg: bg)
    c.device(bezel, in: NSRect(x: CGFloat(outW) * 0.04, y: CGFloat(outW) * 0.035, width: devW, height: devH),
             shadow: 0.35, content: macDesktop(window))
    c.writeJPEG(out)
case "hero":
    let window = load(a[2]), macBezel = Bezel(path: a[3]), phone = load(a[4]), phoneBezel = Bezel(path: a[5])
    let out = a[6], outW = Int(a[7])!, outH = Int(a[8])!, bg = color(a[9])
    let W = CGFloat(outW), H = CGFloat(outH)
    let c = Canvas(outW, outH, bg: bg)
    // A soft ember glow behind the devices; it fades to the background colour
    // well inside the frame, so the image edge stays invisible on the page.
    let glowC = CGPoint(x: W * 0.5, y: H * 0.42)
    let glow = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(),
        colors: [NSColor(srgbRed: 1, green: 0.40, blue: 0.18, alpha: 0.30).cgColor,
                 NSColor(srgbRed: 1, green: 0.40, blue: 0.18, alpha: 0).cgColor] as CFArray, locations: [0, 1])!
    c.ctx.drawRadialGradient(glow, startCenter: glowC, startRadius: 0, endCenter: glowC,
                             endRadius: min(W, H) * 0.62, options: [])
    // MacBook: centred slightly left, bottom-aligned; iPhone overlaps its right
    // edge in front, standing on the same baseline.
    let macW = W * 0.80
    let macH = macW * macBezel.size.height / macBezel.size.width
    let macFrame = NSRect(x: W * 0.06, y: H * 0.02, width: macW, height: macH)
    c.device(macBezel, in: macFrame, shadow: 0.5, content: macDesktop(window))
    let phoneH = macH * 0.86
    let phoneW = phoneH * phoneBezel.size.width / phoneBezel.size.height
    let phoneFrame = NSRect(x: W * 0.94 - phoneW, y: H * 0.02, width: phoneW, height: phoneH)
    c.device(phoneBezel, in: phoneFrame, shadow: 0.6, content: fillScreen(phone))
    c.writeJPEG(out)
default:
    fputs("unknown command \(a[1])\n", stderr); exit(1)
}
