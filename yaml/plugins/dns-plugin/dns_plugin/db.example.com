$TTL 5m ; Default TTL

; SOA, NS and A record for DNS server itself
@                 3600 IN SOA  ns admin ( 2014010800 ; Serial
                                          3600       ; Refresh
                                          3600       ; Retry
                                          3600       ; Expire
                                          300 )      ; Minimum TTL
@                 3600 IN NS   ns
ns                3600 IN A    1.0.0.1 ; IPv4 address of BIND server
ns                3600 IN AAAA 1::1    ; IPv6 address of BIND server

; bono
; ====
;
; Per-node records - not required to have both IPv4 and IPv6 records
bono-1                 IN A    10.67.79.5 
;
; Cluster A and AAAA records - UEs that don't support RFC 3263 will simply
; resolve the A or AAAA records and pick randomly from this set of addresses.
bono                   IN A     15.126.215.206
;
; NAPTR and SRV records - these indicate a preference for TCP and then resolve
; to port 5060 on the per-node records defined above.
@                      IN NAPTR 1 1 "S" "SIP+D2T" "" _sip._tcp
@                      IN NAPTR 2 1 "S" "SIP+D2U" "" _sip._udp
_sip._tcp              IN SRV   0 0 5060 bono-1
_sip._udp              IN SRV   0 0 5060 bono-1

; sprout
; ======
;
; Per-node records - not required to have both IPv4 and IPv6 records
sprout-1               IN A     10.67.79.50 
;
; Cluster A and AAAA records - P-CSCFs that don't support RFC 3263 will simply
; resolve the A or AAAA records and pick randomly from this set of addresses.
sprout                 IN A     10.67.79.50
;
; NAPTR and SRV records - these indicate TCP support only and then resolve
; to port 5054 on the per-node records defined above.
sprout                 IN NAPTR 1 1 "S" "SIP+D2T" "" _sip._tcp.sprout
_sip._tcp.sprout       IN SRV   0 0 5054 sprout-1
_sip._tcp.sprout       IN SRV   0 0 5054 sprout-2
;
; Per-node records for I-CSCF (if enabled) - not required to have both
; IPv4 and IPv6 records 
;
; Cluster A and AAAA records - P-CSCFs that don't support RFC 3263 will simply
; resolve the A or AAAA records and pick randomly from this set of addresses.
; icscf.sprout           IN A     3.0.0.3
;
; NAPTR and SRV records for I-CSCF (if enabled) - these indicate TCP
; support only and then resolve to port 5052 on the per-node records
; defined above.
icscf.sprout           IN NAPTR 1 1 "S" "SIP+D2T" "" _sip._tcp.icscf.sprout
_sip._tcp.icscf.sprout IN SRV   0 0 5052 sprout-3

; homestead
; =========
;
; Per-node records - not required to have both IPv4 and IPv6 records
homestead-1            IN A     10.67.79.53 
;
; Cluster A and AAAA records - sprout picks randomly from these.
hs                     IN A     10.67.79.53 
;
; (No need for NAPTR or SRV records as homestead doesn't handle SIP traffic.)

; homer
; =====
;
; Per-node records - not required to have both IPv4 and IPv6 records
homer-1                IN A     10.67.79.54 
homer                  IN A     10.67.79.54
;
; (No need for NAPTR or SRV records as homer doesn't handle SIP traffic.)

; ralf
; =====
;
; Per-node records - not required to have both IPv4 and IPv6 records
ralf-1                IN A     10.67.79.55 
; Cluster A and AAAA records - sprout and bono pick randomly from these.
ralf                  IN A     10.67.79.55
;
; (No need for NAPTR or SRV records as ralf doesn't handle SIP traffic.)

; ellis
; =====
;
; ellis is not clustered, so there's only ever one node.
;
; Per-node record - not required to have both IPv4 and IPv6 records
ellis-1                IN A     10.67.79.52 
;
; "Cluster"/access A and AAAA record
ellis                  IN A     15.126.247.35
