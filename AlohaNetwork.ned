// ---- Module Host: mot tram gui goi ----
simple Host
{
    parameters:
        @display("i=device/pc,#4080ff,20");
        int packetBits = default(1000);              // L: kich thuoc goi (bit)
        double dataRate = default(1e6);              // C: toc do kenh (bps)
        double ackTimeout @unit(s) = default(1.5ms);// thoi gian cho ACK toi da
        int maxRetries = default(-1);   // -1: gửi lại vô hạn; 0: không gửi lại
        int backoffK = default(10);                  // backoff ngau nhien trong [0, K*T]
        int queueCapacity = default(20);             // so goi toi da trong hang doi
    gates:
        inout gate;                                  // 1 cong 2 chieu noi toi Server
}

// ---- Module Server: tram thu, kiem tra va cham ----
simple Server
{
    parameters:
        @display("i=device/server,#ff6040,20");
        int packetBits = default(1000);
        double dataRate = default(1e6);
    gates:
        inout gate[];                                // array gate cho moi host
}

// ---- Mang: N host noi vao 1 server ----
network AlohaNetwork
{
    parameters:
        @display("bgb=600,450");                     // kich thuoc background
        int N = default(20);                         // #host
        double Gnew = default(0.1);                  // tai goi moi chuan hoa = N*lambda*T
        bool slotted = default(false);               // false: Pure, true: Slotted
    types:
        channel Link extends ned.DelayChannel {
            delay = 10us;                            // T_prop
            @display("ls=grey70,1");
        }
    submodules:
        server: Server {
            @display("p=300,225");                   // server o giua
        }
        host[N]: Host {
            @display("p=130,55,ring,170,170");      // host xep vong tron quanh server
        }
    connections:
        for i=0..N-1 {
            host[i].gate <--> Link <--> server.gate++;
        }
}