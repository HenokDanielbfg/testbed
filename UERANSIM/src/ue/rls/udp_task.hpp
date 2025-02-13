//
// This file is a part of UERANSIM project.
// Copyright (c) 2023 ALİ GÜNGÖR.
//
// https://github.com/aligungr/UERANSIM/
// See README, LICENSE, and CONTRIBUTING files for licensing details.
//

#pragma once

#include <cstdint>
#include <unordered_map>
#include <vector>

#include <lib/rls/rls_pdu.hpp>
#include <lib/udp/server.hpp>
#include <ue/types.hpp>
#include <utils/nts.hpp>
#include <string>
#include <prometheus/gauge.h>
#include <prometheus/registry.h>
#include <prometheus/exposer.h>

namespace nr::ue
{

class RlsUdpTask : public NtsTask
{
  private:
    struct CellInfo
    {
        InetAddress address;
        int64_t lastSeen{};
        int dbm{};
        int cellId{};
    };

  private:
    std::unique_ptr<Logger> m_logger;
    udp::UdpServer *m_server;
    NtsTask *m_ctlTask;
    RlsSharedContext* m_shCtx;
    std::vector<InetAddress> m_searchSpace;
    std::unordered_map<uint64_t, CellInfo> m_cells;
    std::unordered_map<int, uint64_t> m_cellIdToSti;
    int64_t m_lastLoop;
    Vector3 m_simPos;
    DoubleVector3 simPos;  // added by Henok
    DoubleVector3 home;  // added by Henok
    DoubleVector3 work;  // added by Henok
    std::optional<Supi> m_supi{}; // added by Henok
    std::shared_ptr<prometheus::Registry> registry;  // added by Henok
    std::shared_ptr<prometheus::Exposer> exposer;  // added by Henok
    prometheus::Family<prometheus::Counter>* destination_visits_family;  // added by Henok


    int m_cellIdCounter;

    friend class UeCmdHandler;

  public:
    explicit RlsUdpTask(TaskBase *base, RlsSharedContext* shCtx, const std::vector<std::string> &searchSpace);
    ~RlsUdpTask() override = default;

  protected:
    void onStart() override;
    void onLoop() override;
    void onQuit() override;

  private:
    void sendRlsPdu(const InetAddress &addr, const rls::RlsMessage &msg);
    void receiveRlsPdu(const InetAddress &addr, std::unique_ptr<rls::RlsMessage> &&msg);
    void onSignalChangeOrLost(int cellId);
    void heartbeatCycle(uint64_t time, const Vector3 &simPos);

  public:
    void initialize(NtsTask *ctlTask);
    void send(int cellId, const rls::RlsMessage &msg);
};

} // namespace nr::ue
