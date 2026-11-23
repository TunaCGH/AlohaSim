#include <omnetpp.h>
#include <vector>
using namespace omnetpp;

class Server : public cSimpleModule
{
  private:
    struct Rx { int gateIdx; simtime_t created; };
    std::vector<Rx> period;                  // các gói trong chu kỳ bận hiện tại
    cMessage *endTimer = nullptr;
    bool busy = false;
    simtime_t T, busyUntil;
    long rxPackets = 0, okPackets = 0, collidedPackets = 0, collisionEvents = 0;
    cStdDev delayStat;
    cOutVector delayVec;

    void finishPeriod();

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

  public:
    virtual ~Server() { cancelAndDelete(endTimer); }
};

Define_Module(Server);

void Server::initialize()
{
    T = (double)par("packetBits").intValue() / par("dataRate").doubleValue();
    endTimer = new cMessage("endOfReception");
    delayVec.setName("delay");
}

void Server::handleMessage(cMessage *msg)
{
    if (msg == endTimer) {                        // chu kỳ bận kết thúc
        finishPeriod();
        return;
    }

    cPacket *pkt = check_and_cast<cPacket*>(msg);
    int g = pkt->getArrivalGate()->getIndex();    // gói đến từ host nào

    // Nếu chu kỳ cũ vừa hết đúng lúc gói mới đến -> đóng chu kỳ cũ trước
    if (busy && simTime() >= busyUntil) {
        cancelEvent(endTimer);
        finishPeriod();
    }

    rxPackets++;
    period.push_back({g, pkt->getTimestamp()});
    EV_INFO << "t=" << simTime() << " SERVER RX start from host[" << g << "]\n";

    if (!busy) {                                  // mở chu kỳ bận mới
        busy = true;
        busyUntil = simTime() + T;
        scheduleAt(busyUntil, endTimer);
    } else if (simTime() + T > busyUntil) {       // gói chồng lấn -> kéo dài chu kỳ
        busyUntil = simTime() + T;
        cancelEvent(endTimer);
        scheduleAt(busyUntil, endTimer);
    }
    delete pkt;
}

void Server::finishPeriod()
{
    busy = false;
    if (period.size() == 1) {                     // chỉ 1 gói -> thành công
        okPackets++;
        double d = (simTime() - period[0].created).dbl();
        delayStat.collect(d);
        delayVec.record(d);
        send(new cMessage("ACK"), "gate$o", period[0].gateIdx);
        EV_INFO << "t=" << simTime() << " SERVER SUCCESS host[" << period[0].gateIdx << "]\n";
    } else {                                      // >=2 gói -> va chạm, không ACK
        collisionEvents++;
        collidedPackets += period.size();
        EV_INFO << "t=" << simTime() << " SERVER COLLISION of " << period.size() << " packets\n";
    }
    period.clear();
}

void Server::finish()
{
    double simT = simTime().dbl(), Ts = T.dbl();
    recordScalar("N", (double)getParentModule()->par("N").intValue());
    recordScalar("Gnew", getParentModule()->par("Gnew").doubleValue());
    recordScalar("S", okPackets * Ts / simT);                  // thông lượng chuẩn hóa
    recordScalar("G", rxPackets * Ts / simT);                  // tải thực (gồm truyền lại)
    recordScalar("collisionRatio", rxPackets ? (double)collidedPackets / rxPackets : 0.0);
    recordScalar("meanDelay", delayStat.getMean());
    recordScalar("rxPackets", rxPackets);
    recordScalar("okPackets", okPackets);
    recordScalar("collisionEvents", collisionEvents);
}
