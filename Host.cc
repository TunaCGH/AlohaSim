#include <omnetpp.h>
#include <deque>
using namespace omnetpp;

class Host : public cSimpleModule
{
  private:
    bool slotted;
    int packetBits, queueCap, backoffK;
    simtime_t T, ackTimeout;
    double lambdaNode;                       // tốc độ sinh gói của MỖI host

    cMessage *genTimer = nullptr;            // hẹn giờ sinh gói mới
    cMessage *txTimer = nullptr;             // hẹn giờ bắt đầu truyền
    cMessage *ackTimer = nullptr;            // hẹn giờ chờ ACK

    std::deque<cPacket*> queue;              // hàng đợi gói chờ gửi
    cPacket *current = nullptr;              // gói đang cố gửi
    long generated = 0, dropped = 0, attempts = 0, delivered = 0;
    int maxRetries, retries = 0;
    long lost = 0;

    void tryStart();
    void scheduleTx(simtime_t delay);

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

  public:
    virtual ~Host();
};

Define_Module(Host);

void Host::initialize()
{

    cModule *net = getParentModule();
    slotted = net->par("slotted");
    int N = net->par("N");
    double Gnew = net->par("Gnew");

    packetBits = par("packetBits");
    double rate = par("dataRate");
    queueCap = par("queueCapacity");
    backoffK = par("backoffK");
    ackTimeout = par("ackTimeout").doubleValue();

    T = packetBits / rate;                        // T = L/C
    lambdaNode = Gnew / (N * T.dbl());            // từ G = N*lambda*T

    genTimer = new cMessage("gen");
    txTimer = new cMessage("tx");
    ackTimer = new cMessage("ackTimeout");
    scheduleAt(exponential(1.0 / lambdaNode), genTimer);
    maxRetries = par("maxRetries");
}

void Host::scheduleTx(simtime_t delay)
{
    simtime_t t = simTime() + delay;
    if (slotted) {                                // làm tròn lên ranh giới slot
        int64_t Tr = T.raw();
        int64_t k = (t.raw() + Tr - 1) / Tr;
        t = SimTime::fromRaw(k * Tr);
    }
    scheduleAt(t, txTimer);
}

void Host::tryStart()
{
    if (current || queue.empty()) return;
    current = queue.front();
    queue.pop_front();
    retries = 0;
    scheduleTx(SIMTIME_ZERO);
}

void Host::handleMessage(cMessage *msg)
{
    if (msg == genTimer) {                        // 1) có gói mới
        generated++;
        if ((int)queue.size() + (current ? 1 : 0) >= queueCap) {
            dropped++;                            // hàng đợi đầy -> bỏ
        } else {
            queue.push_back(new cPacket("data")); // thời điểm tạo = lúc sinh gói
            tryStart();
        }
        scheduleAt(simTime() + exponential(1.0 / lambdaNode), genTimer);
    }
    else if (msg == txTimer) {                    // 2) đến giờ truyền
        cPacket *p = new cPacket("data");
        p->setBitLength(packetBits);
        p->setTimestamp(current->getCreationTime());  // nhớ lúc sinh gói gốc để tính trễ
        send(p, "gate$o");
        attempts++;
        EV_INFO << "t=" << simTime() << " " << getFullName() << " TX start\n";
        scheduleAt(simTime() + ackTimeout, ackTimer);
    }
    else if (msg == ackTimer) {                   // 3) hết giờ mà chưa có ACK -> va chạm
        EV_INFO << "t=" << simTime() << " " << getFullName() << " TIMEOUT\n";
        if (maxRetries >= 0 && retries >= maxRetries) {
            lost++;
            EV_INFO << "t=" << simTime() << " " << getFullName() << " packet LOST (khong gui lai)\n";// hết số lần gửi lại -> bỏ gói
            delete current;
            current = nullptr;
            tryStart();
        } else {
            retries++;
            EV_INFO << "t=" << simTime() << " " << getFullName() << " -> backoff\n";
            scheduleTx(uniform(0, backoffK * T.dbl()));
        }
    }
    else {                                        // 4) nhận được ACK
        cancelEvent(ackTimer);
        delivered++;
        delete current;
        current = nullptr;
        delete msg;
        tryStart();                               // gửi tiếp gói kế trong hàng đợi
    }
}

void Host::finish()
{
    recordScalar("generated", generated);
    recordScalar("dropped", dropped);
    recordScalar("attempts", attempts);
    recordScalar("delivered", delivered);
}

Host::~Host()
{
    cancelAndDelete(genTimer);
    cancelAndDelete(txTimer);
    cancelAndDelete(ackTimer);
    delete current;
    for (auto *p : queue) delete p;
}
