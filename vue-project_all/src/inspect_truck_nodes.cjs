const fs = require('fs');
const path = require('path');

const glbPath = path.join(__dirname, '../public/Dashboard/models/Accident_Occur1.glb');

try {
  const buffer = fs.readFileSync(glbPath);
  const chunkLength = buffer.readUInt32LE(12);
  const jsonStr = buffer.toString('utf8', 20, 20 + chunkLength);
  const gltf = JSON.parse(jsonStr);

  console.log('Nodes in Accident_Occur1.glb:');
  gltf.nodes.forEach((node, idx) => {
    console.log(`Node #${idx}: Name: "${node.name || 'unnamed'}"`, 
                node.translation ? `Translation: [${node.translation.join(', ')}]` : '',
                node.scale ? `Scale: [${node.scale.join(', ')}]` : '');
  });
} catch (err) {
  console.error('Error:', err);
}
