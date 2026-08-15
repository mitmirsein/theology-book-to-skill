# theology-book-to-skill

한국어 · [English](README.en.md)

신학과 철학 연구를 위한 증거 추적형 book-to-skill 특화판임. 사용 권한이 있는 도서를 에이전트 스킬로 변환하되, 분야별 관점, 출처 구간, 원자적 주장, 제한된 교차 도서 검색을 함께 제공함.

이 저장소에는 변환기와 연구 워크플로만 포함됨. 저작권이 있는 도서, 전체 추출 텍스트, 해당 도서에서 생성한 노트는 배포하지 않음.

## 핵심 기능

- 신학·철학 렌즈: 교리적 로키, 원어 용어, 논증, 방법론, 인물, 성경 참조를 구조화함.
- `segments.json`: 추출 텍스트와 PDF 쪽, EPUB spine 항목, 또는 텍스트 제목·행 범위를 결정론적으로 연결함.
- `claim-index.json`: 한 권의 도서에 대한 원자적 주장, 증거 위치, 검증 상태를 엄격하게 관리함.
- `claim-catalog.json`: 무제한 텍스트 덤프 대신 작고 설명 가능한 교차 도서 증거 묶음을 반환함.
- 검증 절차: 생성 후보와 원전을 재독하여 확인한 `source-checked` 주장을 구별함.

## 생성물

기본 변환 결과는 마스터 `SKILL.md`, 장별 파일, 보조 자료를 갖춘 에이전트 스킬임. 신학·철학 워크플로는 다음 파일을 추가로 사용함.

| 파일 | 용도 |
| --- | --- |
| `segments.json` | 추출 텍스트의 이식 가능한 출처 추적 정보 |
| `claim-index.json` | 한 권에 대한 출처 연결 원자적 주장 |
| `claim-catalog.json` | 재생성 가능한 교차 도서 검색 색인 |
| `lexicon.md` | 전문 용어와 원어 어휘 |
| `core_arguments.md` | 논증, 교리적 입장, 주요 구별 |
| `methodology.md` | 해석과 연구 방법 |

출처 파일 자체는 이 색인에 복사하지 않음. 출처 식별에는 로컬 절대 경로가 아니라 파일명과 SHA-256 다이제스트를 사용함.

## 빠른 시작

저장소를 받은 뒤, 소유하거나 처리 권한이 있는 도서에 추출 명령을 실행함.

```bash
git clone https://github.com/mitmirsein/theology-book-to-skill.git
cd theology-book-to-skill
uv sync --all-extras
uv run book-to-skill path/to/book.pdf
```

생성된 도서 디렉터리에서는 주장 카탈로그를 만들고 질의할 수 있음.

```bash
python3 tools/build_claim_catalog.py --books-root "$SKILLS_HOME"
python3 tools/query_claim_catalog.py --catalog "$SKILLS_HOME/claim-catalog.json" --term "성육신" --scripture "John 1:14" --match all
```

출처 귀속의 정확성이 필요한 주장은 `source-checked` 상태의 기록만 사용해야 함. 생성된 주장은 후보이며, 원전을 재독하고 위치 정보를 붙이기 전에는 검증된 주장으로 표시하지 않음.

## 연구 안전장치

- 정확성이 중요한 경우 주장 색인만으로 판단하지 말고 원전을 다시 열어 확인할 것.
- 도서를 검증하거나 갱신할 때는 쪽 위치와 출처 다이제스트를 함께 보존할 것.
- 저작권이 있는 도서에서 생성한 스킬이나 주장 색인은 필요한 권리가 없는 한 공개하지 말 것.
- PDF, EPUB, 전체 추출 텍스트, API 키, 기기별 경로를 커밋하지 말 것.

## 저장소 구성

```text
book_to_skill/       변환기, 출처 추적, 주장, 카탈로그 코드
tools/               카탈로그 구축, 질의, 검증 도구
tests/               코드 표면 자동 검증
docs/                아키텍처와 운영 문서
SKILL.md             연구 스킬 생성용 에이전트 워크플로
```

특화 연구 스킬의 정본은 이 저장소에 복제하지 않고 별도의 정본 스킬 라이브러리에서 관리함. 변환기는 독립적으로 쓸 수 있게 유지하면서 워크플로의 단일 정본을 보장하기 위함임.

## 원본 프로젝트에 대한 감사

이 프로젝트는 Virgilio의 [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill)을 기반으로 한 독립 특화판임. 원본 프로젝트는 범용 도서-에이전트-스킬 변환기의 토대를 제공했으며, 이 특화판은 그 위에 구축됨.

MIT 라이선스에 따라 원본 저작권 고지를 유지함.

> Copyright (c) 2025 virgiliojr94

이 특화판은 분야 렌즈, 출처 추적, 주장 색인, 교차 도서 증거 검색 기능을 추가하여 관리함. 업스트림 개선은 특화 연구의 보장 조건을 해치지 않도록 검토한 뒤 선별 통합함.

## 라이선스

MIT 라이선스임. [LICENSE.md](LICENSE.md) 참조. 라이선스는 이 변환기와 문서에 적용되며, 사용자가 처리하는 도서나 문서에는 적용되지 않음.
