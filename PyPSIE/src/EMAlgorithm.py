import scipy.optimize as opt
import scipy.sparse as spa
import numpy as np
import json
import time

class EMAlgorithm:
    #@profile
    def __init__(self, kmerHasher):
        self.EPS = 1e-30
        self.NG = kmerHasher.NG
        self.NE = kmerHasher.NE
        self.K = kmerHasher.K
        self.NW = kmerHasher.NW
        self.readLength = kmerHasher.readLength
        
        self.initialIndice()
        self.initialCoefficients(kmerHasher)
        self.initialConstraints()
        
    #@profile
    def initialIndice(self):
        self.NX = []
        for g in range(self.NG):
            self.NX.append(int(self.NE[g] * (self.NE[g] + 1) / 2))
            
        self.NXSUM = [0]
        for g in range(self.NG):
            self.NXSUM.append(self.NX[g] + self.NXSUM[g])
            
        self.MergeIdx = {}
        self.SplitIdx = []
        idx = 0
        for g in range(self.NG):
            for e in range(self.NE[g]):
                self.SplitIdx.append((g,e,e))
                self.MergeIdx[(g,e,e)] = idx
                idx += 1
            for ei in range(self.NE[g]):
                for ej in range(ei + 1, self.NE[g]):
                    self.SplitIdx.append((g,ei,ej))
                    self.MergeIdx[(g,ei,ej)] = idx
                    idx += 1        

    #@profile
    def initialCoefficients(self, kmerHasher):
        self.L = []
        for g in range(self.NG):
            self.L.append(np.zeros((1, self.NX[g])))
        for g in range(self.NG):
            col = 0
            for e in range(self.NE[g]):
                st = kmerHasher.geneBoundary[g][e][0]
                ed = kmerHasher.geneBoundary[g][e][1] + 1
                self.L[g][0, col] = ed - st - self.readLength + 1
                col += 1
            for ei in range(self.NE[g]):
                ej = ei + 1
                while ej < self.NE[g]:
                    self.L[g][0, col] = 2 * self.readLength - 2 - self.readLength + 1
                    ej += 1
                    col += 1
        
        for x in self.L:
            print(x)

        #self.Tau = spa.lil_matrix((self.NW, self.NXSUM[self.NG]))
        self.Tau = []
        for g in range(self.NG):
            self.Tau.append(spa.lil_matrix((self.NW, self.NX[g])))
            
            
        self.W = np.zeros((1, self.NW))
        self.MuNonZero = []
        row = 0
        for kmer in kmerHasher.kmerTable:
            self.W[0, row] = kmerHasher.kmerTable[kmer][0]
            contribution = kmerHasher.kmerTable[kmer][1]
            
            gSet = {}
            for loc in contribution:
                sub = loc.split(',')
                g = int(sub[0])
                ei = int(sub[1])
                ej = int(sub[2])
                col = self.MergeIdx[(g, ei, ej)]
                
                #self.Tau[row, col] = contribution[loc]
                col = col - self.NXSUM[g]
                self.Tau[g][row, col] = contribution[loc]
                
                gSet[g] = True
                
            for g in gSet:
                self.MuNonZero.append((row, g))
            row += 1
        #print(len(self.Tau[0].nonzero()[0]))
            
    #@profile
    def initialConstraints(self):
        self.NA = []
        for g in range(self.NG):
            if self.NE[g] > 2:
                self.NA.append(3 * self.NE[g] - 4)
            else:
                self.NA.append(self.NE[g])
            
        self.A = []
        for g in range(self.NG):
            self.A.append(np.zeros((self.NA[g], self.NX[g])))
        for g in range(self.NG):
            if self.NA[g] == 1:
                self.A[g][0, 0] = 1
                break
            
            row = 0
            
            NRightJunc = self.NE[g] - 1
            l = self.NE[g]
            r = l + self.NE[g] - 1
            while row < NRightJunc:
                self.A[g][row, row] = 1
                for i in range(l, r):
                    self.A[g][row, i] = -1
                l = r
                r = r + self.NE[g] - (row + 2)
                row += 1
            
            NLeftJunc = NRightJunc + self.NE[g] - 1
            while row < NLeftJunc:
                self.A[g][row, row - NRightJunc + 1] = 1
                l = self.NE[g]
                r = row - NRightJunc
                i = 1
                while r >= 0:
                    self.A[g][row, l + r] = -1
                    l += self.NE[g] - i
                    i += 1
                    r -= 1     
                row += 1                
            
            NPsi = NLeftJunc + self.NE[g] - 2
            while row < NPsi:
                for i in range(self.NX[g]):
                    if i >= self.NE[g]:
                        self.A[g][row, i] = -1 
                    elif i != row - NLeftJunc + 1:
                        self.A[g][row, i] = 1
                row += 1                
                
            self.A[g] = self.A[g] / (np.ones((self.NA[g], 1)).dot(self.L[g]))
    
    #@profile
    def initialX(self, g):
        ret = np.random.rand(1, self.NX[g])
        for e in range(self.NE[g]):
            ret[0, e] *= 100
        tot = 0.0
        for e in range(self.NX[g]):
            tot += ret[0, e]
        for e in range(self.NX[g]):
            ret[0, e] /= tot
                
        while not (self.A[g].dot(ret.T) > -self.EPS).all():
            ret = np.random.rand(1, self.NX[g])
            for e in range(self.NE[g]):
                ret[0, e] *= 100
            tot = 0.0
            for e in range(self.NX[g]):
                tot += ret[0, e]
            for e in range(self.NX[g]):
                ret[0, e] /= tot
        return ret

    #@profile
    def initialVariables(self):
        self.Z = np.random.rand(1, self.NG)
        tot = 0.0
        for g in range(self.NG):
            tot += self.Z[0, g]
        for g in range(self.NG):
            self.Z[0, g] /= tot
        
        self.X = []
        for g in range(self.NG):
            self.X.append(self.initialX(g))

        #self.Mu = spa.lil_matrix((self.NW, self.NG))
        return
    
    #@profile
    def eStep(self):
        #=======================================================================
        # tot = []
        # for s in range(self.NW):
        #     tot.append(0)
        # for loca in self.MuNonZero:
        #     s = loca[0]
        #     g = loca[1]
        #     #self.Mu[s, g] = self.Z[0, g] * self.Tau[s, self.NXSUM[g]:self.NXSUM[g+1]].dot(self.X[g].T)[0, 0]
        #     self.Mu[s, g] = self.Z[0, g] * self.Tau[g][s,].dot(self.X[g].T)[0, 0]
        #     
        #     tot[s] += self.Mu[s, g]
        # for loca in self.MuNonZero:
        #     s = loca[0]
        #     g = loca[1]
        #     self.Mu[s, g] /= tot[s]
        #=======================================================================
        self.Mu = []
        tot = np.zeros((self.NW, 1))
        for g in range(self.NG):
            self.Mu.append(np.multiply(self.Tau[g].dot(self.X[g].T), self.Z[0, g]))
            tot += self.Mu[g]        
        for g in range(self.NG):
            self.Mu[g] = spa.lil_matrix(np.divide(self.Mu[g], tot))            
            
        print('look at me!!!' + str(self.Mu[0].sum()))
        print(self.W.sum())
        print(self.Z)
        return
     
    #@profile
    def mStep(self, t):
        tot = 0.0
        for g in range(self.NG):
            self.Z[0, g] = self.Mu[g].T.dot(self.W.T)
            tot += self.Z[0, g]
        for g in range(self.NG):
            self.Z[0, g] /= tot
 
        for g in range(self.NG):
            self.optimizeQ(g, t)
            #pass
        return
    
    #@profile
    def optimizeQ(self, g, t):
        timeSt = time.clock() 
        
        glopt = float('inf')
        
        #xInit = self.initialX(g)
        xInit = self.X[g].copy()
        print('Gene ' + str(g))
        #print(self.A[g].dot(self.X[g].T))
        #===================================================================
        # print((self.A[g].dot(self.X[g].T) >= 0).all())
        # print(np.ones((1, self.NX[g])).dot(self.X[g].T))
        #===================================================================
        res = opt.minimize(fun = self.QFunction,
                           x0 = xInit,
                           args = (g,),
                           tol = self.EPS, 
                           bounds = [(0, 1) for i in range(self.NX[g])],
                           method = 'SLSQP',
                           jac = self.QDerivate,
                           constraints = ({'type':'ineq',
                                           'fun':lambda X: self.A[g].dot(X.T),
                                           'jac':lambda X: self.A[g]},
                                          {'type':'eq', 
                                           'fun':lambda X: np.ones((1, self.NX[g])).dot(X.T) - 1,
                                           'jac':lambda X: np.ones((1, self.NX[g]))}),
                           options = {#'eps' : 1000,
                                      'maxiter' : t,
                                      'ftol' : self.EPS,
                                      #'disp' : True
                                      }
                       )

        #===================================================================
        # res = opt.fmin_slsqp(func = self.QFunction, 
        #                      x0 = xInit, 
        #                      f_eqcons = lambda X, g: np.ones((1, self.NX[g])).dot(X.T) - 1, 
        #                      f_ieqcons = lambda X, g: self.A[g].dot(X.T), 
        #                      bounds = [(0, 1) for i in range(self.NX[g])], 
        #                      fprime = self.QDerivate, 
        #                      fprime_eqcons = lambda X, g: np.ones((1, self.NX[g])), 
        #                      fprime_ieqcons = lambda X, g: self.A[g], 
        #                      args = (g,), 
        #                      iter = 100,
        #                      acc = self.EPS, 
        #                      disp = False, 
        #                      full_output = True, 
        #                      epsilon = self.EPS)
        #===================================================================            

        #=======================================================================
        #     print(res.fun)
        #     if res.fun[0, 0] < glopt:
        #         finres = res
        #         glopt = res.fun[0, 0]
        # print(finres)
        #=======================================================================
        print(res.fun)
        print(res.message)
        self.X[g] = np.matrix(res.x)               
        print(self.X[g].sum())
        
        #=======================================================================
        #     print(res[1])
        #     if res[1][0, 0] < glopt:
        #         finres = res
        #         glopt = res[1][0, 0]
        # print(finres)
        # self.X[g] = np.matrix(finres[0])
        #=======================================================================
        print('Time: ' + str(time.clock() - timeSt) + ' s')
        return
    
    #@profile 
    def offlineProcess(self):
        self.coef = []
        for g in range(self.NG):
            self.coef.append(spa.lil_matrix(self.Mu[g].multiply(self.W.T)))
        return
    
    #@profile 
    def QFunction(self, X, g):
        X = np.matrix(X)
        #temp = self.Tau[:,self.NXSUM[g]:self.NXSUM[g+1]].dot(X.T)
        temp = self.Tau[g].dot(X.T)
        
        #=======================================================================
        # if not (not (self.Mu[:g] > self.EPS) or temp > self.EPS).all():
        #     return np.matrix(float('inf'))
        #=======================================================================
        #return -self.Mu[:,g].multiply(np.log(temp)).T.dot(self.W.T)
        return -self.coef[g].T.dot(np.log(temp))
    
    #@profile
    def QDerivate(self, X, g):
        X = np.matrix(X)
        
        #=======================================================================
        # den = (self.Tau[:,self.NXSUM[g]:self.NXSUM[g+1]].dot(X.T)).dot(np.ones((1, self.NX[g])))
        # den = self.Tau[:,self.NXSUM[g]:self.NXSUM[g+1]] / den
        # num = (spa.lil_matrix(self.Mu[:,g].dot(np.ones((1, self.NX[g]))))).multiply(den)
        # jac = self.W.dot(num)
        #=======================================================================
        
        #coef = self.Mu[:,g].multiply(self.W.T)
        #denom = self.Tau[:, self.NXSUM[g]:self.NXSUM[g+1]].dot(X.T)
        denom = self.Tau[g].dot(X.T)
        #temp = np.divide(coef, denom)
        temp = np.divide(self.coef[g].todense(), denom)
        #jac = self.Tau[:, self.NXSUM[g]:self.NXSUM[g+1]].T.dot(temp).T
        jac = self.Tau[g].T.dot(temp).T
        
        jac /= np.sum(jac)
        return -jac.A1
         
    #===========================================================================
    # def likelihoodFunction(self, x):
    #     temp = np.zeros((self.NW, 1))
    #     x = np.matrix(x)
    #     for g in range(self.NG):
    #         temp += self.Z[0, g] * self.Tau[:,self.NXSUM[g]:self.NXSUM[g+1]].dot(x.T)
    #     temp = scp.log(temp)
    #     return -self.W.dot(temp)
    #===========================================================================
     
    #===========================================================================
    # def optimizeLikelihood(self):
    #     res = opt.minimize(fun = self.likelihoodFunction,
    #                        x0 = self.X[0],
    #                        bounds = [(0, 1) for i in range(self.NX[0])],
    #                        constraints = ({'type':'ineq', 'fun': lambda x: self.A[0].dot(x.T)},
    #                                       {'type':'eq', 'fun': lambda x: np.ones((1, self.NX[0])).dot(x.T) - 1 }))
    #     return res
    #===========================================================================

    def uniformInit(self):
        for g in range(self.NG):
            self.Z[0, g] = 1.0 / self.NG
            e = 0;
            while e < self.NE[g]:
                self.X[g][0, e] = 0.8/self.NE[g]
                e += 1
            while e < self.NX[g]:
                self.X[g][0, e] = 0.2/(self.NX[g] - self.NE[g])
                e += 1

    #@profile
    def work(self, time):
        self.initialVariables()
        self.uniformInit()
        
                
        #=======================================================================
        # res = self.optimizeLikelihood()        
        # print(res)
        # self.X[0] = np.matrix(res.x)
        #=======================================================================
        prevZ = self.Z.copy()
        print(self.Z)
        proc = 0
        #time = 1
        while proc < time:
            if proc % 1 == 0:
                print('\n\n+++++' + str(proc) + ' iteration processed...')
            proc += 1
            self.eStep()
            self.offlineProcess()
            self.mStep(100)
            
            #===================================================================
            # print('===============Debug==================')
            # print(self.X[0])
            # print(self.A[0].dot(self.X[0].T) > -self.EPS)
            # print(self.X[0].sum())
            # print('Tau[0] = ' + str(self.Tau[0].sum()))
            #  
            # print(len(self.Mu[0].nonzero()[0]))
            # print(self.Mu[0].shape)
            # print(self.Mu[0].sum())
            # print(len(self.coef[0].nonzero()[0]))
            # print(self.coef[0].shape)
            # print(self.coef[0].sum())
            #  
            #  
            # temp = self.QFunction(self.X[0], 0)
            # print('QFunc(0) = ', end = '')
            # print(temp)
            # print('QGrad(0) = [')
            # for x in self.QDerivate(self.X[0], 0):
            #     print(x)
            # print(']')
            # print('===============Debug==================')
            #===================================================================
            
            print('Comparing Z...')
            print(prevZ)
            print(self.Z)
            if (np.fabs(self.Z-prevZ) < 1e-5).all():
                print('\nConverged!\n')
                break 
            else:
                prevZ = self.Z.copy()
        #self.mStep(20)
        self.computePSI()
        return

    #@profile 
    def computePSI(self):
        self.Psi = []
        for g in range(self.NG):
            tempPsi = self.X[g] / self.L[g]
            sumEx = 0.0
            sumJu = 0.0
            e = 0
            while e < self.NE[g]:
                sumEx += tempPsi[0, e]
                e += 1
            while e < self.NX[g]:
                sumJu += tempPsi[0, e]
                e += 1
            tempPsi /= (sumEx - sumJu)
            self.Psi.append(tempPsi[0,:self.NE[g]].A1.tolist())
        print(self.Psi)
        psiFile = open('../output/PsiResult.json', 'w')
        json.dump(self.Psi, psiFile)

        return
