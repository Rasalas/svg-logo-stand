const canvas = document.querySelector("canvas");
const context = canvas.getContext("2d");
const spread = document.querySelector("#spread");
const variant = document.querySelector("#variant");
let yaw, pitch;
function resetView() {
  yaw = 0.39;
  pitch = 0.19;
  spread.value = variant.value === "large" ? 27 : 0;
  draw();
}
function draw() {
  const width = canvas.clientWidth, height = canvas.clientHeight;
  const ratio = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  context.scale(ratio, ratio);
  const large = variant.value === "large";
  const gap = Number(spread.value);
  const scale = large ? Math.min(width/(685+gap*5),height/(315+gap*2)) : Math.min(width/219,height/114);
  let shiftX = 0;
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  function project(x, y, z) {
    x += shiftX - (large ? 290 : 91);
    y -= large ? 105 : 31;
    z -= large ? 16 + gap*1.25 : 6 + gap/2;
    const depth = -sy*x + cy*z;
    return [width/2 + scale*(cy*x + sy*z), height/2 - scale*(cp*y - sp*depth), sp*y + cp*depth];
  }
  function face(points) {
    context.moveTo(...points[0].slice(0,2));
    for (const [x,y] of points.slice(1)) context.lineTo(x,y);
    context.closePath();
  }
  function solid(rings, bottom, top, blue) {
    const sides = [], caps = [];
    for (const ring of rings) {
      const back = ring.map(([x,y])=>project(x,y,bottom));
      const front = ring.map(([x,y])=>project(x,y,top));
      caps.push(cp*cy >= 0 ? front : back);
      for (let i=0;i<ring.length;i++) {
        const j=(i+1)%ring.length;
        const dx=ring[j][0]-ring[i][0], dy=ring[j][1]-ring[i][1];
        const length=Math.hypot(dx,dy);
        if (!length || (-sy*cp*dy - sp*dx)<=0) continue;
        const light = (dy*.35 - dx*.72)/length;
        sides.push({points:[front[i],back[i],back[j],front[j]],depth:(front[i][2]+back[j][2])/2,light});
      }
    }
    sides.sort((a,b)=>a.depth-b.depth);
    for (const side of sides) {
      context.beginPath(); face(side.points);
      const shade = .79 + .14*side.light;
      context.fillStyle = 'rgb('+ (blue?[10,53,83]:[240,229,210]).map(v=>Math.round(v*shade)).join(',')+')';
      context.strokeStyle=context.fillStyle; context.lineWidth=.65;
      context.fill(); context.stroke();
    }
    context.beginPath(); caps.forEach(face);
    context.fillStyle = blue ? '#003057' : '#f4ebdb';
    context.fill('evenodd');
  }
  if (large) {
    const objects = [];
    assembly.panels.forEach(([bottom, middle, top], index) => {
      const offset = (index-1)*gap*2.6;
      const center = (bottom[0][0][0] + offset);
      objects.push({offset, depth: -sy*center*cp+cy*cp*16, layers:[
        [bottom,0,26.5,false],[middle,26.5,31,false],[top,31,32,false]
      ]});
    });
    assembly.inserts.forEach(([piece, pin]) => {
      const center = pin[0].reduce((total,p)=>total+p[0],0)/pin[0].length;
      const offset = (center<225 ? -1 : center<386 ? 0 : 1)*gap*2.6;
      const z = 31+gap*3;
      objects.push({offset, depth:-sy*(center+offset)*cp+cy*cp*z, layers:[
        [pin,z-4,z,true],[piece,z,z+5,true]
      ]});
    });
    objects.sort((a,b)=>a.depth-b.depth);
    // For near-frontal views draw the relief only after its backing.
    if (Math.abs(cy)>0.55) objects.sort((a,b)=>(Number(a.layers[0][3])-Number(b.layers[0][3]))*Math.sign(cy));
    for(const obj of objects){
      shiftX=obj.offset;
      if(cp*cy<0) obj.layers.reverse();
      obj.layers.forEach(layer=>solid(...layer));
    }
    return;
  }
  const layers=[
    [contours[0],0,8.65,false],
    [fitContours[0],8.65,11.4,false],
    [fitContours[1],11.4,12,false],
    [fitContours[2],9+gap,11.4+gap,true],
    [contours[1],11.4+gap,13.6+gap,true],
  ];
  if(cp*cy<0) layers.reverse();
  layers.forEach(layer=>solid(...layer));
}
let drag;
canvas.onpointerdown = event => {
  canvas.setPointerCapture(event.pointerId);
  drag=[event.clientX,event.clientY];
};
function rotate(dx,dy) {
  yaw+=dx; pitch=Math.max(-1.55,Math.min(1.55,pitch+dy)); draw();
}
canvas.onpointermove = event => {
  if(!drag) return;
  rotate((event.clientX-drag[0])*.012,(event.clientY-drag[1])*.012);
  drag=[event.clientX,event.clientY];
};
canvas.onlostpointercapture = ()=>{drag=null};
canvas.onkeydown = event => {
  const delta={ArrowLeft:[-.12,0],ArrowRight:[.12,0],ArrowUp:[0,.12],ArrowDown:[0,-.12]}[event.key];
  if(delta){event.preventDefault();rotate(...delta)}
};
spread.oninput=draw;
variant.onchange=()=>{
  document.querySelector("#size").textContent=variant.value==="large" ? "600 × 216 × 36 mm" : "189,9 × 68,4 × 13,6 mm";
  resetView();
};
document.querySelector('#reset').onclick=resetView;
resetView();
new ResizeObserver(draw).observe(canvas);
