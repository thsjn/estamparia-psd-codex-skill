# Estamparia PSD para Codex

Skill para criar estampas têxteis com motivos raster separados, rapport verificável, barrado de colocação, textura opcional e PSD em camadas.

## Instalação

Clone este repositório na pasta de skills do Codex, mantendo `SKILL.md` na raiz da pasta `estamparia-psd`. Invoque a skill com `$estamparia-psd` ao pedir uma estampa. A geração dos motivos usa a skill `imagegen` do ambiente Codex; o compositor local transforma PNGs transparentes em módulos e PSD.

Para executar o compositor, instale as dependências de [requirements.txt](requirements.txt) em um ambiente Python e prepare um manifesto conforme [references/manifest.md](references/manifest.md):

```powershell
python -m pip install -r requirements.txt
python scripts/compose_psd.py --manifest manifest.json --verify
```

O compositor gera o módulo de rapport, uma prévia 2 × 2, a arte de colocação, o PSD e um relatório de verificações. Se houver barrado, ele é entregue em PNG transparente separado e aplicado somente à arte de colocação.

Consulte [SKILL.md](SKILL.md) para o fluxo completo. A saída é RGB de 8 bits; trabalhos que exijam CMYK, perfil ICC específico ou especificações de gráfica precisam de adaptação e conferência na produção.
