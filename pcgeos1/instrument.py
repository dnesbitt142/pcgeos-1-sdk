from __future__ import annotations

def instrument(text:str,max_gap:int=8):
    out=[];intext=False;need=True;count=0;polls=0;instructions=0;repeats=0
    for line in text.splitlines():
        st=line.strip()
        if st.startswith('.section'): intext='.text' in st
        elif st=='.text': intext=True
        elif st in ('.data','.bss'): intext=False
        if intext and st.endswith(':'): need=True
        if intext and st and not st.startswith(('.', '#')) and not st.endswith(':'):
            op=st.split()[0]
            # GCC and Clang may spell repeat ops slightly differently.
            if op.startswith('rep'):
                parts=st.replace('\t',' ').split()
                suffix=parts[-1]
                suffix=suffix.removesuffix('l')+'l' if suffix in ('movsl','stosl') else suffix
                if suffix not in ('movsl','movsb','stosb','stosl'):
                    raise ValueError('Unsupported repeat instruction: '+st)
                tag=f'.Lpcg_repeat_{repeats}';repeats+=1
                out.extend(['\tpushfl',f'\tjecxz {tag}_done',tag+':','\tcall native_poll','\t'+suffix,'\tdecl %ecx',f'\tjnz {tag}',tag+'_done:','\tpopfl'])
                polls+=1;instructions+=1;need=True;count=0;continue
            if need or count>=max_gap:
                out.append('\tcall\tnative_poll');polls+=1;need=False;count=0
            out.append(line);count+=1;instructions+=1
            if op.startswith(('j','call','ret')): need=True
        else:
            out.append(line)
    return '\n'.join(out)+'\n',{'poll_sites':polls,'original_instructions':instructions,
                                 'bounded_repeat_expansions':repeats,
                                 'maximum_straight_line_instructions_between_polls':max_gap}
