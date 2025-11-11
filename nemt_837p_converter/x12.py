# SPDX-License-Identifier: MIT
import datetime

class ControlNumbers:
    def __init__(self, isa=1, gs=1, st=1):
        self.isa = int(isa)
        self.gs = int(gs)
        self.st = int(st)
    def next_isa(self): v=self.isa; self.isa+=1; return v
    def next_gs(self): v=self.gs; self.gs+=1; return v
    def next_st(self): v=self.st; self.st+=1; return v

class X12Writer:
    def __init__(self, element_sep="*", segment_term="~", component_sep=":", repetition_sep="^"):
        self.element_sep = element_sep
        self.segment_term = segment_term
        self.component_sep = component_sep
        self.repetition_sep = repetition_sep
        self._segments = []
    def _pad(self, s, length, pad_char=" "):
        s = "" if s is None else str(s)
        return s[:length].ljust(length, pad_char)
    def _zero(self, n, length): return str(int(n)).zfill(length)
    def _fmt_time(self, t):
        if isinstance(t, datetime.datetime): return t.strftime("%H%M")
        s = str(t or "")
        return s.replace(":","")[:4] or datetime.datetime.now().strftime("%H%M")
    def _escape(self, s):
        if s is None: return ""
        s = str(s)
        for ch in (self.element_sep, self.segment_term, self.component_sep, self.repetition_sep):
            s = s.replace(ch, " ")
        return s
    def composite(self, *components):
        return self.component_sep.join(self._escape(c) for c in components if c not in (None,""))
    def segment(self, tag, *elements):
        parts = [tag] + [self._escape(e) for e in elements]
        self._segments.append(self.element_sep.join(parts) + self.segment_term)
    def extend(self, raw_segment):
        if not raw_segment.endswith(self.segment_term):
            raise ValueError("Segment must end with terminator")
        self._segments.append(raw_segment)
    def build_ISA(self, sender_qual, sender_id, receiver_qual, receiver_id,
                  usage_indicator="T", control_number=1, date=None, time=None, version="00501"):
        if date is None: date = datetime.datetime.now()
        if time is None: time = datetime.datetime.now()
        d = date.strftime("%y%m%d")
        t = self._fmt_time(time)
        self._segments.append(self.element_sep.join([
            "ISA","00", self._pad("",10), "00", self._pad("",10),
            self._pad(sender_qual,2), self._pad(sender_id,15),
            self._pad(receiver_qual,2), self._pad(receiver_id,15),
            d, t, "^", self._pad(version,5), self._zero(control_number,9),
            "0", self._pad(usage_indicator,1), self.component_sep
        ]) + self.segment_term)
    def build_IEA(self, num_groups, control_number):
        self.segment("IEA", str(num_groups), self._zero(control_number,9))
    def build_GS(self, functional_id_code, app_sender_code, app_receiver_code,
                 date=None, time=None, control_number=1, version="005010X222A1"):
        if date is None: date = datetime.datetime.now()
        if time is None: time = datetime.datetime.now()
        d = date.strftime("%Y%m%d")
        t = self._fmt_time(time)
        self.segment("GS", functional_id_code, app_sender_code, app_receiver_code, d, t, str(control_number), "X", version)
    def build_GE(self, num_tx_sets, control_number):
        self.segment("GE", str(num_tx_sets), str(control_number))
    def build_ST(self, impl_guide_version="005010X222A1", control_number=1):
        self.segment("ST", "837", str(control_number), impl_guide_version)
    def build_SE(self, start_index, control_number):
        count = len(self._segments) - start_index + 1
        self.segment("SE", str(count), str(control_number))
    def to_string(self): return "".join(self._segments)
