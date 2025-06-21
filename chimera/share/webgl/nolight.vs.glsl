// just like default.vs.glsl except all lights are ignored
#define LIGHT_MAX 8

attribute vec3 position;
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
  vec4 mvPosition = worldMatrix * vec4(position, 1.0);
  
  lightWeighting = vec3(1.0, 1.0, 1.0);
  
  vColor = color;
  vTexCoord = texCoord1;
  gl_Position = projectionMatrix * mvPosition;
}
