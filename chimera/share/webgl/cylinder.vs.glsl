// just like default.vs.glsl expect for additional tranformation
#define LIGHT_MAX 8

attribute vec3 position;
attribute vec4 transformX, transformY, transformZ;	// 4x3 transformation
attribute float yscale;
attribute vec3 normal;
attribute vec4 color;
attribute vec2 texCoord1;

uniform mat4 worldMatrix;
uniform mat4 viewMatrix;
uniform mat4 projectionMatrix;
uniform mat4 worldInverseTransposeMatrix;

uniform bool enableLights;
uniform vec3 ambientColor;
uniform vec3 directionalColor;
uniform vec3 lightingDirection;

uniform vec3 pointLocation[LIGHT_MAX];
uniform vec3 pointColor[LIGHT_MAX];
uniform int numberPoints;

varying vec4 vColor;
varying vec2 vTexCoord;
varying vec3 lightWeighting;

void main(void) {
  vec4 pos = vec4(position * vec3(1.0, yscale, 1.0), 1.0);
  vec4 mvPosition;
  mvPosition.x = dot(pos, transformX);
  mvPosition.y = dot(pos, transformY);
  mvPosition.z = dot(pos, transformZ);
  mvPosition.w = pos.w;
  pos = worldMatrix * mvPosition;
  mvPosition = pos;
  vec3 n;
  n.x = dot(normal, vec3(transformX));
  n.y = dot(normal, vec3(transformY));
  n.z = dot(normal, vec3(transformZ));
  
  if(!enableLights) {
    lightWeighting = vec3(1.0, 1.0, 1.0);
  } else {
    vec3 plightDirection;
    vec3 pointWeight = vec3(0.0, 0.0, 0.0);
    //vec3 transformedNormal = mat3(worldInverseTransposeMatrix) * n;
    vec3 transformedNormal = vec3(worldInverseTransposeMatrix * vec4(n, 0.0));
    float directionalLightWeighting = max(dot(transformedNormal, lightingDirection), 0.0);
    for (int i = 0; i < LIGHT_MAX; i++) {
      if (i < numberPoints) {
        plightDirection = normalize((viewMatrix * vec4(pointLocation[i], 1.0)).xyz - mvPosition.xyz);
        pointWeight += max(dot(transformedNormal, plightDirection), 0.0) * pointColor[i];
      } else {
        break;
      }
    }

    lightWeighting = ambientColor + (directionalColor * directionalLightWeighting) + pointWeight;
  }
  
  vColor = color;
  vTexCoord = texCoord1;
  gl_Position = projectionMatrix * mvPosition;
}
