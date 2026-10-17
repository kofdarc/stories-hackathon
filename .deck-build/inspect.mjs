import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('reports/Stories_Recommendations_ELI5.pptx'));
console.log((await p.inspect({kind:'slide,layout',maxChars:12000})).ndjson);
console.log('masters',p.masters.items.length);
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];
 await fs.writeFile(`.deck-build/source-${i+1}.png`,new Uint8Array(await (await p.export({slide:s,format:'png',scale:.7})).arrayBuffer()));
}
await fs.writeFile('.deck-build/source-shapes.json',JSON.stringify(p.slides.items.map(s=>s.shapes.items.map(x=>({id:x.id,name:x.name,text:x.text?.toString(),position:x.position}))),null,2));
