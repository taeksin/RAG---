import pyperclip

def process_text(text):
    # 텍스트 내 <<SPLIT>>를 <<BLOCKEND>>로 변경 (필요시)
    text = text.replace("<<SPLIT>>", "<<BLOCKEND>>")
    
    # <<BLOCKEND>>를 기준으로 블록 분리
    raw_blocks = text.split("<<BLOCKEND>>")
    blocks = []
    for block in raw_blocks:
        block = block.strip()
        if block:  # 빈 블록은 제외
            blocks.append(block)
    
    # 각 블록에서 헤더와 내용 분리하기
    # 만약 블록에 한 줄밖에 없으면 그 줄 전체를 body로 처리
    parsed_blocks = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) > 1:
            header = lines[0]
            body = "\n".join(lines[1:])
        else:
            header = ""
            body = block  # 한 줄짜리는 body로 처리
        parsed_blocks.append((header, body))
    
    # 두번째 블록부터 이전 블록의 내용 마지막 100자를 현재 블록의 내용 앞에 추가
    overlapped_blocks = []
    for i, (header, body) in enumerate(parsed_blocks):
        if i > 0:
            prev_body = parsed_blocks[i-1][1]
            overlap = prev_body[-100:] if len(prev_body) >= 100 else prev_body
            body = overlap + "\n  " + body
        overlapped_blocks.append((header, body))
    
    # 오버랩이 적용된 블록들을 다시 <<SPLIT>>로 결합 (각 블록은 헤더와 본문으로 구성)
    modified_blocks = []
    for header, body in overlapped_blocks:
        if header:  # 헤더가 있으면 헤더+개행+본문
            block_text = header + "\n" + body if body else header
        else:
            block_text = body
        modified_blocks.append(block_text)
    
    modified_content = ("\n<<SPLIT>>\n").join(modified_blocks) + "\n<<SPLIT>>"
    return modified_content

if __name__ == "__main__":
    text = """이러한 치료법 중 하나는 EMDR(Eye
Movement Desensitization and
Reprocessing)이다. EMDR은 원래 외상 후 스
트레스 장애(PTSD) 치료에 효과적이라고 알려
져 있으나, 최근 연구들은 우울증 환자에게도 긍
정적인 효과를 보일 수 있음을 시사하고 있다
[3,4]. 일반적으로 EMDR 치료는 모니터 화면을
통해 환자의 눈동자 움직임을 유도하여 기억을
재처리하는 방식으로 이루어졌다.
<<Split>>
최근 연구에서 VR 기술을 이용하여 만성 뇌 질
환 재활치료의 가능성을 제기[5]하고 있다. 옥
스퍼드 대학의 연구에서는 VR이 불안 장애 등
정신 질환 치료에 효과적으로 활용될 수 있음을
확인하였다[6]. VR(가상현실) 기술을 활용함으
로써 보다 몰입감 있는 치료 환경을 제공할 수
있어, VR이 기존의 모니터 기반 EMDR보다 더
높은 치료 효과를 낼 수 있다는 가능성이 제기되
고 있다[7]. 특히, 뇌파 분석을 통해 우울증 환
자의 뇌 상태를 더욱 깊이 이해할 수 있으며, 베
타파는 우울증과 관련된 주요 뇌파로 연구되고
있다[8,9]. 베타파는 높은 각성과 불안과 밀접하
게 연관된 것으로 알려져 있으며, 우울증 환자들
에게서 이러한 높은 베타파가 관찰된다는 연구
가 있다[10]. 이는 우울증 환자들이 과도한 불안
과 스트레스를 경험하고 있다는 점은, 이러한 신
경학적 각성 상태가 우울증 증상을 악화시키는
주요 요인 중 하나로 작용할 수 있음을 시사한
다. 이러한 맥락에서, 우울증 치료에 있어 베타파
변화를 관찰하는 것은 중요한 접근법으로 주목
받고 있다.
<<Split>>
본 연구는 그동안 베타파가와 우울증과의 관계
를 증명하는 연구가 제한적으로 진행되고 있는
상황에서 베타파 감소가 우울증 증상 개선에 직
간접적인 관계를 확인하는 것이며 VR을 활용한
EMDR 치료가 기존의 모니터 기반 EMDR 치료
에 비해 우울증 환자의 베타파에 미치는 영향을
검증하는 데 목적을 둔다. 특히, 기존 EMDR 치
료에 VR 기술을 도입함으로써 우울증 치료 효과
<<Split>>
www.kci.go.kr
<<Split>>
를 강화할 가능성을 탐구하며, 이를 통해 실증적
데이터를 확보하는 것을 주요 연구 과제로 삼았
다. VR 기반 EMDR 치료가 우울증 환자의 뇌파,
특히 베타파에 미치는 영향을 측정함으로써, 가
상현실의 활용 가능성과 치료적 유용성을 평가
하는 데 연구의 의의를 두고 있다.
<<Split>>
따라서 본 연구는 모니터 기반 치료와 VR 기반
치료 간의 유의미한 차이를 규명하고, 우울증 치
료 방법으로서 VR의 잠재력을 탐색하고자 한다.
이는 우울증 치료에 대한 보다 다양한 접근법을
제시함과 동시에, 새로운 디지털 기술을 활용한
정신 건강 치료의 가능성을 확장하는 데 중요한
의미를 갖는다.
<<Split>>
# II. 본 론
<<Split>>
1. EMDR과 우울증
<<Split>>
EMDR(Eye Movement Desensitization and
Reprocessing, 이하 EMDR)은 안구운동 민감소
실 재처리 기법을 이용한 치료로써 1987년
Francine Shapiro 박사에 의해 개발된 심리 치
료 기법으로, 양측성 안구운동이 외상 기억과 연
관된 부정적인 감정의 강도를 감소시키는데 도
움이 된다고 주장하였고 주로 외상 후 스트레스
장애(PTSD) 치료에서 효과가 검증된 방법으로
알려져 있다[11].
<<Split>>
EMDR의 기본 원리는 외상 기억이 부적절하게
처리되어 부정적인 감정과 신념을 유발하며, 치
료 과정을 통해 이러한 기억을 재처리하여 적응
적인 방식으로 통합하도록 돕는다.
<<Split>>
치료는 8단계로 구성되어 있다[3]. 1단계는
'병력 조사 및 치료 계획 수립단계'로써 환자의
과거 역사와 현재 상태를 평가하여 맞춤형 치료
계획을 수립한다. 2단계는 '준비 단계'로써 환자
에게 EMDR의 개념과 절차를 설명하고, 안정화
기법을 소개하여 치료 과정에서 안정감을 느끼
도록 한다. 3단계는 '평가 단계' 단계로써 해결해
야 할 특정 기억을 선택하고, 그와 관련된 감정"""
    
    modified_text = process_text(text)
    print(modified_text)
    pyperclip.copy(modified_text)
    print("\n[클립보드에 복사되었습니다.]")
