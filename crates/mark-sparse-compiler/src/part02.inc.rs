fn otsu_histogram(image: &GrayImage, region: Region) -> u8 {
    let mut hist = [0u64; 256];
    for y in region.y..region.y + region.height {
        for x in region.x..region.x + region.width {
            hist[image.get_pixel(x, y).0[0] as usize] += 1;
        }
    }
    let total: u64 = hist.iter().sum();
    let sum: u64 = hist.iter().enumerate().map(|(i, n)| i as u64 * *n).sum();
    let mut weight_b = 0u64;
    let mut sum_b = 0u64;
    let mut best = 127u8;
    let mut best_between = -1.0f64;
    for t in 0..256usize {
        weight_b += hist[t];
        if weight_b == 0 { continue; }
        let weight_f = total.saturating_sub(weight_b);
        if weight_f == 0 { break; }
        sum_b += t as u64 * hist[t];
        let mean_b = sum_b as f64 / weight_b as f64;
        let mean_f = (sum - sum_b) as f64 / weight_f as f64;
        let between = weight_b as f64 * weight_f as f64 * (mean_b - mean_f).powi(2);
        if between > best_between { best_between = between; best = t as u8; }
    }
    best
}

fn resolved_threshold(image: &GrayImage, observation: &Observation) -> Result<u8> {
    if observation.segmentation.polarity != "dark_on_light" {
        bail!("v7 compiler currently requires dark_on_light segmentation; observation {} requested {}", observation.id, observation.segmentation.polarity);
    }
    match &observation.segmentation.threshold {
        Value::String(s) if s == "otsu" => Ok(otsu_histogram(image, observation.region)),
        Value::Number(n) => n.as_u64().filter(|v| *v <= 255).map(|v| v as u8).ok_or_else(|| anyhow!("invalid threshold for {}", observation.id)),
        other => bail!("unsupported threshold {:?} for {}", other, observation.id),
    }
}

fn validate_region(image: &GrayImage, region: Region, id: &str) -> Result<()> {
    let right = region.x as u64 + region.width as u64;
    let bottom = region.y as u64 + region.height as u64;
    if region.width == 0 || region.height == 0 || right > image.width() as u64 || bottom > image.height() as u64 {
        bail!("observation {id} region {:?} exceeds source {}x{}", region, image.width(), image.height());
    }
    Ok(())
}

#[derive(Clone, Copy)]
struct Tile {
    core_x: u32, core_y: u32, core_w: u32, core_h: u32,
    ext_x: u32, ext_y: u32, ext_w: u32, ext_h: u32,
}

fn tiles(region: Region, tile_size: u32, overlap: u32) -> Vec<Tile> {
    let mut out = Vec::new();
    let mut cy = 0u32;
    while cy < region.height {
        let ch = tile_size.min(region.height - cy);
        let mut cx = 0u32;
        while cx < region.width {
            let cw = tile_size.min(region.width - cx);
            let ext_left = cx.saturating_sub(overlap);
            let ext_top = cy.saturating_sub(overlap);
            let ext_right = (cx + cw + overlap).min(region.width);
            let ext_bottom = (cy + ch + overlap).min(region.height);
            out.push(Tile { core_x: cx, core_y: cy, core_w: cw, core_h: ch, ext_x: ext_left, ext_y: ext_top, ext_w: ext_right-ext_left, ext_h: ext_bottom-ext_top });
            cx += cw;
        }
        cy += ch;
    }
    out
}

fn tile_mask(image: &GrayImage, region: Region, tile: Tile, threshold: u8) -> Vec<u8> {
    let mut mask = vec![0u8; (tile.ext_w * tile.ext_h) as usize];
    for y in 0..tile.ext_h {
        for x in 0..tile.ext_w {
            let gx = region.x + tile.ext_x + x;
            let gy = region.y + tile.ext_y + y;
            if image.get_pixel(gx, gy).0[0] <= threshold { mask[(y * tile.ext_w + x) as usize] = 1; }
        }
    }
    mask
}

const N8: [(i32, i32); 8] = [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)];

fn neighbor_index(i: usize, dir: usize, w: usize, h: usize) -> Option<usize> {
    let x=i%w; let y=i/w; let (dx,dy)=N8[dir]; let nx=x as i32+dx; let ny=y as i32+dy;
    if nx<0 || ny<0 || nx>=w as i32 || ny>=h as i32 { None } else { Some(ny as usize*w+nx as usize) }
}

fn degree8(mask: &[u8], i: usize, w: usize, h: usize) -> u8 {
    let mut n=0; for d in 0..8 { if let Some(j)=neighbor_index(i,d,w,h) { n += (mask[j]!=0) as u8; } } n
}

fn thin(input: &[u8], w: usize, h: usize) -> Vec<u8> {
    let mut pixels=input.to_vec(); let mut remove=vec![0u8;input.len()]; let mut changed=true; let mut iterations=0usize;
    while changed && iterations<120 {
        iterations+=1; changed=false;
        for phase in 0..2 {
            remove.fill(0); let mut remove_count=0usize; if w<3 || h<3 { continue; }
            for y in 1..h-1 { for x in 1..w-1 {
                let i=y*w+x; if pixels[i]==0 { continue; }
                let p2=pixels[(y-1)*w+x]; let p3=pixels[(y-1)*w+x+1]; let p4=pixels[y*w+x+1]; let p5=pixels[(y+1)*w+x+1];
                let p6=pixels[(y+1)*w+x]; let p7=pixels[(y+1)*w+x-1]; let p8=pixels[y*w+x-1]; let p9=pixels[(y-1)*w+x-1];
                let ns=[p2,p3,p4,p5,p6,p7,p8,p9]; let n:u8=ns.iter().sum(); if !(2..=6).contains(&n) { continue; }
                let transitions=(0..8).filter(|k| ns[*k]==0 && ns[(*k+1)%8]!=0).count(); if transitions!=1 { continue; }
                let ok=if phase==0 { p2*p4*p6==0 && p4*p6*p8==0 } else { p2*p4*p8==0 && p2*p6*p8==0 };
                if ok { remove[i]=1; remove_count+=1; }
            }}
            if remove_count>0 { changed=true; for (i,mark) in remove.iter().enumerate() { if *mark!=0 { pixels[i]=0; } } }
        }
    }
    pixels
}
